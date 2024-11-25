import os
import json
import time
import logging
import board
import busio
from adafruit_pn532.i2c import PN532_I2C
from typing import List, Dict, Optional

class NFCMusicAssociator:
    def __init__(self, music_dir: str, nfc_data_file: str):
        self.logger = logging.getLogger("NFCMusicAssociator")
        self.music_dir = os.path.abspath(music_dir)  # Convertit en chemin absolu
        self.nfc_data_file = nfc_data_file
        
        # Initialisation NFC
        try:
            self.logger.info("Initializing I2C bus...")
            self.i2c = busio.I2C(board.SCL, board.SDA)
            
            self.logger.info("Initializing PN532...")
            self.pn532 = PN532_I2C(self.i2c, debug=False)
            
            self.logger.info("Configuring PN532...")
            self.pn532.SAM_configuration()
                
        except Exception as e:
            self.logger.error(f"NFC initialization error: {str(e)}")
            raise

    def load_nfc_data(self) -> List[Dict]:
        """Charge les données NFC existantes"""
        try:
            if os.path.exists(self.nfc_data_file):
                with open(self.nfc_data_file, 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            self.logger.error(f"Error loading NFC data: {e}")
            return []

    def save_nfc_data(self, data: List[Dict]):
        """Sauvegarde les données NFC"""
        try:
            with open(self.nfc_data_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving NFC data: {e}")

    def get_music_files(self) -> List[str]:
        """Récupère la liste des fichiers musicaux"""
        music_files = []
        for root, _, files in os.walk(self.music_dir):
            for file in files:
                if file.lower().endswith(('.mp3', '.wav', '.ogg', '.flac')):
                    full_path = os.path.abspath(os.path.join(root, file))
                    music_files.append(full_path)
        return music_files

    def read_nfc_tag(self, timeout: float = 0.5) -> Optional[str]:
        """Lit un tag NFC et retourne son ID"""
        try:
            uid = self.pn532.read_passive_target(timeout=timeout)
            if uid is not None:
                return ':'.join([hex(i)[2:].upper().zfill(2) for i in uid])
            return None
        except Exception as e:
            self.logger.error(f"Error reading NFC tag: {e}")
            return None

    def associate_files(self):
        """Processus principal d'association"""
        nfc_data = self.load_nfc_data()
        music_files = self.get_music_files()
        
        print(f"\nTrouvé {len(music_files)} fichiers musicaux au total.")
        
        # Récupère les chemins absolus des fichiers déjà associés
        associated_files = {os.path.abspath(item['path']) for item in nfc_data}
        associated_tags = {item['idtagnfc'] for item in nfc_data}
        
        print(f"Dont {len(associated_files)} déjà associés.")
        
        # Trouve les fichiers non associés
        unassociated_files = [f for f in music_files if f not in associated_files]
        
        if not unassociated_files:
            print("\nTous les fichiers sont déjà associés !")
            return
            
        print(f"\nTrouvé {len(unassociated_files)} fichiers non associés :")
        for f in unassociated_files:
            print(f"- {os.path.basename(f)}")
        
        try:
            for file_path in unassociated_files:
                file_name = os.path.basename(file_path)
                print(f"\n{'='*50}")
                print(f"Fichier en attente d'association : {file_name}")
                print(f"Chemin complet : {file_path}")
                print("Veuillez scanner un tag NFC... (Ctrl+C pour passer au suivant)")
                
                while True:
                    tag_id = self.read_nfc_tag()
                    if tag_id:
                        if tag_id in associated_tags:
                            print(f"\nERREUR : Ce tag ({tag_id}) est déjà associé à un autre fichier !")
                            print("Veuillez utiliser un autre tag...")
                            time.sleep(1)
                            continue
                            
                        # Ajoute la nouvelle association
                        nfc_data.append({
                            "idtagnfc": tag_id,
                            "path": file_path,
                            "type": 1
                        })
                        associated_tags.add(tag_id)
                        
                        # Sauvegarde immédiate
                        self.save_nfc_data(nfc_data)
                        
                        print(f"Association réussie ! Tag: {tag_id}")
                        break
                        
                    time.sleep(0.1)
                    
        except KeyboardInterrupt:
            print("\n\nAssociation interrompue par l'utilisateur.")
        finally:
            print("\nSauvegarde des associations...")
            self.save_nfc_data(nfc_data)
            print("Terminé !")

if __name__ == "__main__":
    # Configuration du logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Chemins à configurer
    MUSIC_DIR = "music"  # Dossier music dans le répertoire courant
    NFC_DATA_FILE = "nfc_data.json"
    
    try:
        associator = NFCMusicAssociator(MUSIC_DIR, NFC_DATA_FILE)
        associator.associate_files()
        
    except KeyboardInterrupt:
        print("\nProgramme interrompu par l'utilisateur.")
    except Exception as e:
        logging.error(f"Erreur fatale: {e}", exc_info=True)