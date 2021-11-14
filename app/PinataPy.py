import os
import typing as tp
import requests
import logging
from flask.globals import _request_ctx_stack
from flask_appbuilder.filemanager import FileManager, ImageManager, uuid_namegen
from flask_appbuilder.upload import FileUploadField

try:
    from flask import _app_ctx_stack
except ImportError:
    _app_ctx_stack = None

app_stack = _app_ctx_stack or _request_ctx_stack

log = logging.getLogger(__name__)

ResponsePayload = tp.Dict[str, tp.Any]
OptionsDict = tp.Dict[str, tp.Any]
Headers = tp.Dict[str, str]

# global constants
API_ENDPOINT: str = "https://api.pinata.cloud/"

class PinataPy:
    """A pinata api client session object"""

    def __init__(self, pinata_api_key: str, pinata_secret_api_key: str) -> None:
        self._auth_headers: Headers = {
            "pinata_api_key": pinata_api_key,
            "pinata_secret_api_key": pinata_secret_api_key,
        }

    @staticmethod
    def _error(response: requests.Response) -> ResponsePayload:
        """Construct dict from response if an error has occurred"""
        return {"status": response.status_code, "reason": response.reason, "text": response.text}

    def get_object(self, filename):
        pass

    def pin_file_object_to_ipfs(self, file_object):
        url = API_ENDPOINT + "pinning/pinFileToIPFS"
        headers = self._auth_headers
        response: requests.Response = requests.post(url=url, files={'file':file_object}, headers=headers)
        return response.json() if response.ok else self._error(response)

    def pin_file_to_ipfs(self, path_to_file: str, options: tp.Optional[OptionsDict] = None) -> ResponsePayload:
        """
        Pin any file, or directory, to Pinata's IPFS nodes
        More: https://docs.pinata.cloud/api-pinning/pin-file
        """
        url: str = API_ENDPOINT + "pinning/pinFileToIPFS"
        headers: Headers = self._auth_headers

        def get_all_files(directory: str) -> tp.List[str]:
            """get a list of absolute paths to every file located in the directory"""
            paths: tp.List[str] = []
            for root, dirs, files_ in os.walk(os.path.abspath(directory)):
                for file in files_:
                    paths.append(os.path.join(root, file))
            return paths

        files: tp.Dict[str, tp.Any]

        if os.path.isdir(path_to_file):
            all_files: tp.List[str] = get_all_files(path_to_file)
            files = {"file": [(file, open(file, "rb")) for file in all_files]}
        else:
            files = {"file": open(path_to_file, "rb")}

        if options is not None:
            if "pinataMetadata" in options:
                headers["pinataMetadata"] = options["pinataMetadata"]
            if "pinataOptions" in options:
                headers["pinataOptions"] = options["pinataOptions"]
        response: requests.Response = requests.post(url=url, files=files, headers=headers)
        return response.json() if response.ok else self._error(response)  # type: ignore

    def pin_hash_to_ipfs(self, hash_to_pin: str, options: tp.Optional[OptionsDict] = None) -> ResponsePayload:
        """WARNING: This Pinata API method is deprecated. Use 'pin_hash_to_ipfs' instead"""
        url: str = API_ENDPOINT + "pinning/pinHashToIPFS"
        headers: Headers = self._auth_headers
        headers["Content-Type"] = "application/json"
        body = {"hashToPin": hash_to_pin}
        if options is not None:
            if "host_nodes" in options:
                body["host_nodes"] = options["host_nodes"]
            if "pinataMetadata" in options:
                body["pinataMetadata"] = options["pinataMetadata"]
        response: requests.Response = requests.post(url=url, json=body, headers=headers)
        return response.json() if response.ok else self._error(response)  # type: ignore

    def pin_to_pinata_using_ipfs_hash(self, ipfs_hash: str, filename: str) -> ResponsePayload:
        """
        Pin file to Pinata using its IPFS hash
        https://docs.pinata.cloud/api-pinning/pin-by-hash
        """
        payload: OptionsDict = {"pinataMetadata": {"name": filename}, "hashToPin": ipfs_hash}
        url: str = API_ENDPOINT + "/pinning/pinByHash"
        response: requests.Response = requests.post(url=url, json=payload, headers=self._auth_headers)
        return self._error(response) if not response.ok else response.json()  # type: ignore

    def pin_jobs(self, options: tp.Optional[OptionsDict] = None) -> ResponsePayload:
        """
        Retrieves a list of all the pins that are currently in the pin queue for your user.
        More: https://docs.pinata.cloud/api-pinning/pin-jobs
        """
        url: str = API_ENDPOINT + "pinning/pinJobs"
        payload: OptionsDict = options if options else {}
        response: requests.Response = requests.get(url=url, params=payload, headers=self._auth_headers)
        return response.json() if response.ok else self._error(response)  # type: ignore

    def pin_json_to_ipfs(self, json_to_pin: tp.Any, options: tp.Optional[OptionsDict] = None) -> ResponsePayload:
        """pin provided JSON"""
        url: str = API_ENDPOINT + "pinning/pinJSONToIPFS"
        headers: Headers = self._auth_headers
        headers["Content-Type"] = "application/json"
        payload: ResponsePayload = {"pinataContent": json_to_pin}
        if options is not None:
            if "pinataMetadata" in options:
                payload["pinataMetadata"] = options["pinataMetadata"]
            if "pinataOptions" in options:
                payload["pinataOptions"] = options["pinataOptions"]
        response: requests.Response = requests.post(url=url, json=payload, headers=headers)
        return response.json() if response.ok else self._error(response)  # type: ignore

    def remove_pin_from_ipfs(self, hash_to_remove: str) -> ResponsePayload:
        """Removes specified hash pin"""
        url: str = API_ENDPOINT + "pinning/removePinFromIPFS"
        headers: Headers = self._auth_headers
        headers["Content-Type"] = "application/json"
        body = {"ipfs_pin_hash": hash_to_remove}
        response: requests.Response = requests.post(url=url, json=body, headers=headers)
        return self._error(response) if not response.ok else {"message": "Removed"}

    def pin_list(self, options: tp.Optional[OptionsDict] = None) -> ResponsePayload:
        """https://pinata.cloud/documentation#PinList"""
        url: str = API_ENDPOINT + "data/pinList"
        payload: OptionsDict = options if options else {}
        response: requests.Response = requests.get(url=url, params=payload, headers=self._auth_headers)
        return response.json() if response.ok else self._error(response)  # type: ignore

    def user_pinned_data_total(self) -> ResponsePayload:
        url: str = API_ENDPOINT + "data/userPinnedDataTotal"
        response: requests.Response = requests.get(url=url, headers=self._auth_headers)
        return response.json() if response.ok else self._error(response)  # type: ignore


class PinataFileUploadField(FileUploadField):
    """File upload field for Pinata"""

    def __init__(self, label=None, validators=None,
                 filemanager=None,
                 **kwargs):
        """
            Constructor.

            :param label:
                Display label
            :param validators:
                Validators
        """
        super(PinataFileUploadField, self).__init__(label, validators, **kwargs)

        if filemanager is not None:
            self.filemanager = filemanager()
        else:
            self.filemanager = FileManager()
        self._should_delete = False


class PinataFileManager(ImageManager):
    """File upload to Pinata
    """

    def __init__(self,
                 relative_path='',
                 namegen=None,
                 allowed_extensions=None,
                 **kwargs):

        ctx = app_stack.top

        if "PINATA_API_SECRET_KEY" in ctx.app.config:
            self.pinata_secret_api_key = ctx.app.config["PINATA_API_SECRET_KEY"]
        else:
            raise Exception('Config PINATA_API_SECRET_KEY is mandatory')
        if "PINATA_API_KEY" in ctx.app.config:
            self.pinata_api_key = ctx.app.config["PINATA_API_KEY"]
        else:
            raise Exception('Config PINATA_API_KEY is mandatory')

        self.relative_path = relative_path
        self.namegen = namegen or uuid_namegen
        if not allowed_extensions and 'FILE_ALLOWED_EXTENSIONS' in ctx.app.config:
            self.allowed_extensions = ctx.app.config['FILE_ALLOWED_EXTENSIONS']
        else:
            self.allowed_extensions = allowed_extensions
        self._should_delete = False

    def get_ipfs_client(self):
        ipfs = PinataPy(pinata_api_key=self.pinata_api_key, pinata_secret_api_key=self.pinata_secret_api_key)
        return ipfs

    def delete_file(self, filename):
        client = self.get_s3_client()
        file_path = os.path.join(self.relative_path, filename)
        client.delete_object(Bucket=self.bucket_name, Key=file_path)

    def save_file(self, data, filename):
        ipfs = self.get_ipfs_client()
        pin = ipfs.pin_file_object_to_ipfs(file_object=data)
        _filename = 'https://gateway.pinata.cloud/ipfs/' + pin['IpfsHash']
        return _filename

    def save_thumbnail(self, data, filename,thumbnail_size=None):
        ipfs = self.get_ipfs_client()
        thumbnail_size = thumbnail_size or self.thumbnail_size
        pin = ipfs.pin_file_object_to_ipfs(file_object=self.resize(self.image, thumbnail_size))
        _filename = 'https://gateway.pinata.cloud/ipfs/' + pin['IpfsHash']
        return _filename

    def get_file(self, filename):
        ipfs = self.get_ipfs_client()
        response = ipfs.get_object(filename)
        body = response['Body'].read()
        return body
