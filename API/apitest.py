import requests
import config
class interface:
    def __init__(self,api_key='', user='test') -> None:
        self.USERNAME=user
        self.API_URL = config.url #
        self.MATERIALS_URL = f"{self.API_URL}/api/materials"
        self.headers = {
            'Username': self.USERNAME,
            'API-Key': api_key
        }
        pass


    def get_materials(self,api_key=''):
        """Retrieve materials from the database using the API key."""

        response = requests.get(self.MATERIALS_URL, headers=self.headers)
        if response.status_code == 200:
            materials = response.json()
            print("Materials retrieved successfully:")
            for material in materials:
                print(f"ID: {material['id']}, Name: {material['name']}, Quantity: {material['quantity']}")
        else:
            print(f"Error retrieving materials: {response.json().get('error')}")

    def add_material(self, data=dict(name='test', description='test', quantity=1, filename=None)):
        """Add a new material to the database using the API key."""

        files = {}
        if data['filename']:
            files['file'] = open(data['filename'], 'rb')  # Open the file in binary mode if provided

        response = requests.post(self.MATERIALS_URL, headers=self.headers, data=data, files=files)
        
        if response.status_code == 201:
            print(f"Material added successfully: {response.json()}")
        else:
            print(f"Error adding material: {response.json().get('error')}")
    def download_structure(self,material_id=1):
        response = requests.get(f"{self.API_URL}/api/download/{material_id}", headers=self.headers)
        if response.status_code == 200:
            filename = response.headers.get('Content-Disposition').split('filename=')[-1].strip('"')
            with open(filename, 'wb') as f:
                f.write(response.content)
            print(f"File downloaded successfully: {filename}")
        else:
            print(f"Error downloading file: {response.json().get('error')}")
    def get_structure(self,material_id=1):
        response = requests.get(f"{self.API_URL}/api/download/{material_id}", headers=self.headers)
        if response.status_code == 200:
            filename = response.headers.get('Content-Disposition').split('filename=')[-1].strip('"')
            print(f"File downloaded successfully: {filename}")
            return response.content
        else:
            print(f"Error downloading file: {response.json().get('error')}")
            return None
