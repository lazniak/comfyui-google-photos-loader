from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os
import pickle
from cryptography.fernet import Fernet
from .logging_config import log_message

def get_credentials(client_secrets_file, plugin_dir, logger):
    log_message(logger, "Getting credentials", 'info')
    flow = InstalledAppFlow.from_client_secrets_file(
        client_secrets_file,
        scopes=['https://www.googleapis.com/auth/photoslibrary.readonly']
    )
    
    creds = None
    token_path = os.path.join(plugin_dir, 'token.pickle')
    key_path = os.path.join(plugin_dir, 'encryption_key.key')

    if not os.path.exists(key_path):
        key = Fernet.generate_key()
        with open(key_path, 'wb') as key_file:
            key_file.write(key)
    else:
        with open(key_path, 'rb') as key_file:
            key = key_file.read()

    fernet = Fernet(key)

    if os.path.exists(token_path):
        log_message(logger, "Loading existing token", 'info')
        try:
            with open(token_path, 'rb') as token:
                encrypted_token = pickle.load(token)
                if isinstance(encrypted_token, bytes):
                    decrypted_token = fernet.decrypt(encrypted_token)
                    creds = pickle.loads(decrypted_token)
                else:
                    log_message(logger, "Stored token is not in the expected format. Regenerating.", 'warning')
                    creds = None
        except Exception as e:
            log_message(logger, f"Error loading token: {str(e)}. Regenerating.", 'error')
            creds = None
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            log_message(logger, "Refreshing token", 'info')
            creds.refresh(Request())
        else:
            log_message(logger, "Getting new token", 'info')
            creds = flow.run_local_server(port=0)
        
        log_message(logger, "Saving new token", 'info')
        encrypted_token = fernet.encrypt(pickle.dumps(creds))
        with open(token_path, 'wb') as token:
            pickle.dump(encrypted_token, token)
    
    if not creds:
        log_message(logger, "Failed to obtain valid credentials", 'error')
        raise Exception("Failed to obtain valid credentials")

    log_message(logger, "Credentials obtained successfully", 'info')
    return creds