from flask import jsonify, request, render_template
from app import app, aws_manager, active_connections
from version import __version__
import subprocess
import random
import socket
import time
from subprocess import STARTUPINFO, STARTF_USESHOWWINDOW, CREATE_NEW_CONSOLE, SW_HIDE
import tempfile
import os
import logging
from preferences_handler import PreferencesHandler
import threading
import psutil
import tempfile


# Create preferences handler instance
preferences_handler = PreferencesHandler()
#logger = logging.getLogger(__name__)

active_connections = []

@app.route('/api/version')
def get_version():
    """Return the application version from version.py.

    Returns:
        JSON with key 'version' (str), e.g. {"version": "1.31"}.
    """
    return jsonify({'version': __version__})


@app.route('/api/profiles')
def get_profiles():
    """
    Endpoint to get available AWS profiles
    Returns: JSON list of profile names
    """
    try:
        logging.info("Attempting to load AWS profiles")
        profiles = aws_manager.get_profiles()
        return jsonify(profiles)
    except Exception as e:
        # Use proper logging instead of print
        logging.error(f"Failed to load AWS profiles: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to load profiles'}), 500


@app.route('/api/refresh-profiles', methods=['POST'])
def refresh_profiles():
    """Refresh AWS profiles and maintain current connection if possible"""
    try:
        # Store current connection info
        current_profile = aws_manager.profile
        current_region = aws_manager.region
        
        # Get fresh list of profiles
        profiles = aws_manager.get_profiles()
        
        # Check if current profile is still valid
        is_current_valid = current_profile in profiles if current_profile else False
        
        response_data = {
            'status': 'success',
            'profiles': profiles,
            'currentProfile': current_profile if is_current_valid else None,
            'currentRegion': current_region if is_current_valid else None,
            'accountId': aws_manager.account_id if is_current_valid else None
        }
        
        logging.info(f"Profiles refreshed successfully. Found {len(profiles)} profiles")
        return jsonify(response_data)
        
    except Exception as e:
        logging.error(f"Failed to refresh profiles: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/regions')
def get_regions():
    try:
        regions = aws_manager.get_regions()
        return jsonify(regions)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/connect', methods=['POST'])
def connect():
    try:
        data = request.json
        profile = data.get('profile')
        region = data.get('region')
        if not profile or not region:
            return jsonify({'error': 'Profile and region are required'}), 400
        aws_manager.set_profile_and_region(profile, region)
        # Try to list instances immediately to verify connection
        instances = aws_manager.list_ssm_instances()
        
        # Include account ID in the response
        return jsonify({
            'status': 'success',
            'account_id': aws_manager.account_id
        })
        
        if isinstance(instances, dict) and 'error' in instances:
            # Token is expired
            return jsonify({'error': instances['error']}), 401
        return jsonify({'status': 'success'})
    except Exception as e:
        logging.error(f"Connection error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/instances')
def get_instances():
    try:
        instances = aws_manager.list_ssm_instances()
        return jsonify(instances) if instances else jsonify([])
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route('/api/ssh/<instance_id>', methods=['POST'])
def start_ssh(instance_id):
    try:
        data = request.json
        profile = data.get('profile')
        region = data.get('region')
        
        # Crea un ID univoco per la connessione
        connection_id = f"ssh_{instance_id}_{int(time.time())}"
        
        # Crea il comando AWS SSM e avvia il processo
        cmd_command = f'aws ssm start-session --target {instance_id} --region {region} --profile {profile}'
        process = subprocess.Popen(f'start cmd /k "{cmd_command}"', shell=True)
        
        def find_cmd_pid():
            time.sleep(2)  # Wait for process to start
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.name().lower() == 'cmd.exe':
                        cmdline = ' '.join(proc.cmdline()).lower()
                        if cmd_command.lower() in cmdline:
                            return proc.pid
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return None

        # Trova il PID del processo cmd.exe
        cmd_pid = find_cmd_pid()
        
        # Aggiungi alla lista delle connessioni attive
        connection = {
            'connection_id': connection_id,
            'instance_id': instance_id,
            'type': 'SSH',
            'process': process,
            'pid': cmd_pid
        }
        active_connections.append(connection)
        
        # Monitora il processo in un thread separato
        def monitor_process():
            try:
                if cmd_pid:
                    try:
                        proc = psutil.Process(cmd_pid)
                        proc.wait()  # Attendi che il processo termini
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                    finally:
                        # Rimuovi la connessione quando il processo termina
                        global active_connections
                        active_connections[:] = [c for c in active_connections 
                                              if c['connection_id'] != connection_id]
            except Exception as e:
                logging.error(f"Error monitoring SSH process: {str(e)}")
        
        thread = threading.Thread(target=monitor_process, daemon=True)
        thread.start()
        
        return jsonify({
            "status": "success",
            "connection_id": connection_id
        })
        
    except Exception as e:
        logging.error(f"Error starting SSH: {str(e)}")
        return jsonify({"error": str(e)}), 500



@app.route('/api/remote-host-port/<instance_id>', methods=['POST'])
def start_remote_host_port(instance_id):
    """Start port forwarding to remote host with improved monitoring"""
    try:
        data = request.json
        profile = data.get('profile')
        region = data.get('region')
        remote_host = data.get('remote_host')
        remote_port = data.get('remote_port')
        
        # Generate connection ID
        connection_id = f"remote_port_{instance_id}_{int(time.time())}"
        
        # Get free port
        local_port = find_free_port()
        if local_port is None:
            logging.error("Could not find available port for port forwarding")
            return jsonify({'error': 'No available ports'}), 503
            
        logging.info(f"Starting remote host port forwarding - Instance: {instance_id}, Host: {remote_host}, Remote Port: {remote_port}")
        
        # Create AWS command for remote host port forwarding
        aws_command = f'aws ssm start-session --region {region} --target {instance_id} --document-name AWS-StartPortForwardingSessionToRemoteHost --parameters host="{remote_host}",portNumber="{remote_port}",localPortNumber="{local_port}" --profile {profile}'
        
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        
        # Start port forwarding process
        process = subprocess.Popen(
            ["powershell", "-Command", aws_command],
            startupinfo=startupinfo,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Find PowerShell process PID (reuse existing function)
        ps_pid = find_powershell_pid()
            
        # Add to active connections
        connection = {
            'connection_id': connection_id,
            'instance_id': instance_id,
            'type': 'Remote Host Port',
            'local_port': local_port,
            'remote_port': remote_port,
            'remote_host': remote_host,
            'process': process,
            'pid': ps_pid
        }
        active_connections.append(connection)
        
        # Monitor process (reuse existing monitoring logic)
        monitor_thread = threading.Thread(
            target=monitor_process, 
            args=(connection_id, ps_pid),
            daemon=True
        )
        monitor_thread.start()
        
        logging.info(f"Remote host port forwarding started - Instance: {instance_id}, Host: {remote_host}, Port: {remote_port}")
        return jsonify({
            "status": "success",
            "connection_id": connection_id,
            "local_port": local_port,
            "remote_port": remote_port,
            "remote_host": remote_host
        })
        
    except Exception as e:
        logging.error(f"Error starting remote host port forwarding: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/rdp/<instance_id>', methods=['POST'])
def start_rdp(instance_id):
    """Start an RDP session with improved monitoring"""
    try:
        data = request.json
        profile = data.get('profile')
        region = data.get('region')
        
        # Generate connection ID
        connection_id = f"rdp_{instance_id}_{int(time.time())}"
        
        # Get free port
        local_port = find_free_port()
        if local_port is None:
            logging.error("Could not find available port for RDP connection")
            return jsonify({'error': 'No available ports for RDP connection'}), 503
        
        logging.info(f"Starting RDP - Instance: {instance_id}, Port: {local_port}")
        
        # Create AWS command
        aws_command = f"aws ssm start-session --target {instance_id} --document-name AWS-StartPortForwardingSession --parameters portNumber=3389,localPortNumber={local_port} --region {region} --profile {profile}"
        
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        
        # Start port forwarding process
        process = subprocess.Popen(
            ["powershell", "-Command", aws_command],
            startupinfo=startupinfo,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        def find_powershell_pid():
            time.sleep(2)
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.name().lower() == 'powershell.exe':
                        cmdline = ' '.join(proc.cmdline()).lower()
                        if aws_command.lower() in cmdline:
                            return proc.pid
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            return None
            
        # Find PowerShell process PID
        ps_pid = find_powershell_pid()
        
        # Start RDP client
        subprocess.Popen(f'mstsc /v:localhost:{local_port}')
        
        # Add to active connections
        connection = {
            'connection_id': connection_id,
            'instance_id': instance_id,
            'type': 'RDP',
            'local_port': local_port,
            'process': process,
            'pid': ps_pid
        }
        active_connections.append(connection)
        
        # Monitor process
        def monitor_process():
            try:
                if ps_pid:
                    try:
                        proc = psutil.Process(ps_pid)
                        proc.wait()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                    finally:
                        global active_connections
                        active_connections[:] = [c for c in active_connections 
                                              if c['connection_id'] != connection_id]
            except Exception as e:
                logging.error(f"Error monitoring RDP process: {str(e)}")
        
        thread = threading.Thread(target=monitor_process, daemon=True)
        thread.start()
        
        logging.info(f"RDP session started - Instance: {instance_id}, Port: {local_port}")
        return jsonify({
            "status": "success", 
            "connection_id": connection_id,
            "port": local_port
        })
        
    except Exception as e:
        logging.error(f"Error starting RDP: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
    
    
@app.route('/api/instance-details/<instance_id>')
def get_instance_details(instance_id):
    """Get detailed information about a specific EC2 instance"""
    try:
        logging.info(f"Get instance details: {instance_id}")
        details = aws_manager.get_instance_details(instance_id)
        if details is None:
            return jsonify({'error': 'Instance details not found'}), 404
        return jsonify(details)
    except Exception as e:
        logging.error(f"Error getting instance details: {str(e)}")
        return jsonify({'error': str(e)}), 500
    
    
    
@app.route('/api/preferences', methods=['GET'])
def get_preferences():
    """Get current preferences"""
    try:
        return jsonify(preferences_handler.preferences)
    except Exception as e:
        logging.error(f"Error getting preferences: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/preferences', methods=['POST'])
def update_preferences():
    """Update preferences"""
    try:
        new_preferences = request.json
        if preferences_handler.update_preferences(new_preferences):
            return jsonify({'status': 'success'})
        return jsonify({'error': 'Failed to update preferences'}), 500
    except Exception as e:
        logging.error(f"Error updating preferences: {str(e)}")
        return jsonify({'error': str(e)}), 500
    
    
@app.route('/api/refresh', methods=['POST'])
def refresh_data():
    """Refresh instances data"""
    try:
        instances = aws_manager.list_ssm_instances()
        return jsonify({
            "status": "success",
            "instances": instances if instances else []
        })
    except Exception as e:
        print(f"Error refreshing data: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
    
@app.route('/api/custom-port/<instance_id>', methods=['POST'])
def start_custom_port(instance_id):
    """Start custom port forwarding with support for both local and remote host modes"""
    try:
        data = request.json
        profile = data.get('profile')
        region = data.get('region')
        mode = data.get('mode', 'local')  # Default to local mode
        remote_port = data.get('remote_port')
        remote_host = data.get('remote_host')  # Will be None for local mode
        
        # Generate connection ID based on mode
        connection_id = f"port_{mode}_{instance_id}_{int(time.time())}"
        
        # Get free port
        local_port = find_free_port()
        if local_port is None:
            logging.error("Could not find available port for port forwarding")
            return jsonify({'error': 'No available ports'}), 503
            
        # Create appropriate AWS command based on mode
        if mode == 'local':
            logging.info(f"Starting local port forwarding - Instance: {instance_id}, Local: {local_port}, Remote: {remote_port}")
            aws_command = f"aws ssm start-session --target {instance_id} --document-name AWS-StartPortForwardingSession --parameters portNumber={remote_port},localPortNumber={local_port} --region {region} --profile {profile}"
        else:
            logging.info(f"Starting remote host port forwarding - Instance: {instance_id}, Host: {remote_host}, Port: {remote_port}")
            #aws_command = f'aws ssm start-session --region {region} --target {instance_id} --document-name AWS-StartPortForwardingSessionToRemoteHost --parameters host="{remote_host}",portNumber="{remote_port}",localPortNumber="{local_port}" --profile {profile}'
            aws_command = f"aws ssm start-session --target {instance_id} --document-name AWS-StartPortForwardingSessionToRemoteHost --parameters host={remote_host},portNumber={remote_port},localPortNumber={local_port} --region {region} --profile {profile}"
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        
        # Start port forwarding process
        process = subprocess.Popen(
            ["powershell", "-Command", aws_command],
            startupinfo=startupinfo,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Define find_powershell_pid function
        def find_powershell_pid():
            time.sleep(2)
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.name().lower() == 'powershell.exe':
                        cmdline = ' '.join(proc.cmdline()).lower()
                        if aws_command.lower() in cmdline:
                            return proc.pid
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return None
            
        # Find PowerShell process PID
        ps_pid = find_powershell_pid()
        
        # Create connection object with appropriate type and info
        connection = {
            'connection_id': connection_id,
            'instance_id': instance_id,
            'type': 'Remote Host Port' if mode != 'local' else 'Custom Port',
            'local_port': local_port,
            'remote_port': remote_port,
            'remote_host': remote_host if mode != 'local' else None,
            'process': process,
            'pid': ps_pid
        }
        active_connections.append(connection)
        
        # Monitor process
        def monitor_process():
            try:
                if ps_pid:
                    try:
                        proc = psutil.Process(ps_pid)
                        proc.wait()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                    finally:
                        global active_connections
                        active_connections[:] = [c for c in active_connections 
                                              if c['connection_id'] != connection_id]
            except Exception as e:
                logging.error(f"Error monitoring port forwarding process: {str(e)}")
        
        thread = threading.Thread(target=monitor_process, daemon=True)
        thread.start()
        
        response_data = {
            "status": "success",
            "connection_id": connection_id,
            "local_port": local_port,
            "remote_port": remote_port,
        }

        # Add remote_host to response only for remote mode
        if mode != 'local':
            response_data["remote_host"] = remote_host

        logging.info(f"Port forwarding started successfully - Mode: {mode}, Instance: {instance_id}")
        return jsonify(response_data)
        
    except Exception as e:
        logging.error(f"Error starting port forwarding: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/active-connections')
def get_active_connections():
    """Get list of active connections with port information"""
    try:
        active = []
        to_remove = []
        
        for conn in active_connections:
            try:
                is_active = False
                pid = conn.get('pid')
                
                if pid:
                    try:
                        process = psutil.Process(pid)
                        if process.is_running():
                            # Per RDP e Custom Port, verifica anche che la porta sia ancora in uso
                            if conn['type'] in ['RDP', 'Custom Port']:
                                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                try:
                                    result = sock.connect_ex(('127.0.0.1', conn['local_port']))
                                    is_active = (result == 0)  # La porta è in uso
                                finally:
                                    sock.close()
                            else:
                                is_active = True
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                        
                if is_active:
                    connection_info = {
                        'connection_id': conn['connection_id'],
                        'instance_id': conn['instance_id'],
                        'type': conn['type']
                    }
                    
                    # Add port information if available
                    if 'local_port' in conn:
                        connection_info['local_port'] = conn['local_port']
                    if 'remote_port' in conn:
                        connection_info['remote_port'] = conn['remote_port']
                        
                    active.append(connection_info)
                else:
                    to_remove.append(conn)
                    
            except Exception as e:
                logging.error(f"Error checking connection: {str(e)}")
                to_remove.append(conn)
                
        # Remove inactive connections
        for conn in to_remove:
            try:
                active_connections.remove(conn)
            except ValueError:
                pass
                
        return jsonify(active)
        
    except Exception as e:
        logging.error(f"Error getting active connections: {str(e)}")
        return jsonify([])
        


def monitor_process(connection_id, pid):
    """Monitor a specific process and update connection status"""
    try:
        process = psutil.Process(pid)
        while process.is_running():
            try:
                # Verifica che il processo sia ancora un cmd.exe
                if process.name().lower() != 'cmd.exe':
                    break
                time.sleep(1)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    finally:
        # Rimuovi la connessione quando il processo termina
        global active_connections
        active_connections[:] = [c for c in active_connections if c['connection_id'] != connection_id]
        
@app.route('/api/terminate-connection/<connection_id>', methods=['POST'])
def terminate_connection(connection_id):
    """Terminate a connection"""
    try:
        connection = next((c for c in active_connections 
                         if c.get('connection_id') == connection_id), None)
        
        if not connection:
            return jsonify({"error": "Connection not found"}), 404
            
        pid = connection.get('pid')
        if pid:
            try:
                process = psutil.Process(pid)
                # Termina il processo e tutti i suoi figli
                for child in process.children(recursive=True):
                    child.terminate()
                process.terminate()
                
                # Attendi che terminino
                gone, alive = psutil.wait_procs([process], timeout=3)
                for p in alive:
                    p.kill()
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
                
        active_connections[:] = [c for c in active_connections 
                               if c.get('connection_id') != connection_id]
                               
        return jsonify({"status": "success"})
        
    except Exception as e:
        logging.error(f"Error terminating connection: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/set-log-level', methods=['POST'])
def set_log_level():
    """Set the application logging level"""
    try:
        data = request.get_json()
        log_level = data.get('logLevel', 'INFO')
        
        # Convert string level to logging constant
        numeric_level = getattr(logging, log_level.upper())
        
        # Update root logger
        logging.getLogger().setLevel(numeric_level)
        
        # Update specific loggers if needed
        logging.getLogger('werkzeug').setLevel(numeric_level)
        
        return jsonify({'status': 'success'})
    except Exception as e:
        logging.error(f"Error setting log level: {str(e)}")
        return jsonify({'error': str(e)}), 500
    
    
# Utility functions
# Update this function in routes.py
def find_free_port():
    """Find a free port using the configured range"""
    # Get preferences from frontend
    start_port, end_port = preferences_handler.get_port_range()
    logging.debug(f"Finding free port between {start_port} and {end_port}")
    start = start_port
    end = end_port
    max_attempts = 20
    """
    Find a free port in the given range for AWS SSM port forwarding
    Safe implementation for Windows systems
    
    Args:
        start (int): Start of port range (default: 60000)
        end (int): End of port range (default: 60100)
        max_attempts (int): Maximum number of attempts to find a port
    
    Returns:
        int: A free port number or None if no port is found
    """
    logging.debug(f"Searching for free port between {start} and {end}")
    
    used_ports = set()
    for _ in range(max_attempts):
        port = random.randint(start, end)
        
        if port in used_ports:
            continue
            
        used_ports.add(port)
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # Just try to connect to the port
            # If connection fails, port is likely free
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            
            if result != 0:  # Port is available
                logging.info(f"Found free port: {port}")
                return port
            else:
                logging.debug(f"Port {port} is in use")
                
        except Exception as e:
            logging.debug(f"Error checking port {port}: {str(e)}")
        finally:
            sock.close()
    
    logging.error(f"No free port found after {max_attempts} attempts")
    return None

# Add route for serving the main page
@app.route('/')
def home():
    return render_template('index.html')