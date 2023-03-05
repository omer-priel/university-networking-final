# FTP handlers

from io import BytesIO
import logging
import os
import os.path
import shutil
import struct
import zipfile
import threading
from abc import ABC, abstractmethod

from src.app.config import config
from src.app.rudp import create_new_requestID, send_error
from src.app.storage import get_path, in_storage
from src.lib.ftp import BasicLayer, Pocket, PocketSubType, PocketType, pack_directory_block, pack_file_block


# interfaces
class RequestHandler(ABC):
    def __init__(self, request: Pocket, clientAddress: tuple[str, int], storagePath: str):
        self.request = request
        self._clientAddress = clientAddress
        self.requestID = 0
        self._storagePath = storagePath

    @abstractmethod
    def route(self) -> tuple[Pocket, bytes | None] | None:
        ...

    def get_client_address(self) -> tuple[str, int]:
        return self._clientAddress

    def get_requestID(self) -> int:
        return self.requestID

    def get_path(self, path: str) -> str:
        return get_path(path, self._storagePath)

    def send_error(self, errorMessage: str) -> None:
        send_error(errorMessage, self._clientAddress)


class UploadRequestHandler(RequestHandler):
    def __init__(self, request: Pocket, clientAddress: tuple[str, int], storagePath: str):
        RequestHandler.__init__(self, request, clientAddress, storagePath)
        self.segments: dict[int, bytes] = {}
        self.segmentsAmount = 0

    @abstractmethod
    def post_upload(self, data: bytes) -> None:
        ...


class DownloadRequestHandler(RequestHandler):
    def __init__(self, request: Pocket, clientAddress: tuple[str, int], storagePath: str):
        RequestHandler.__init__(self, request, clientAddress, storagePath)
        self.data = b""
        self.windowToSend: list[int] = []
        self.windowSending: list[int] = []
        self.ready = False
        self.response: Pocket = ...  # type: ignore[assignment]
        self.pockets: list[Pocket] = []
        self.locker = threading.Lock()


# handlers
class UploadFileRequestHandler(UploadRequestHandler):
    def route(self) -> tuple[Pocket, bytes | None] | None:
        # validation
        if not self.request.uploadRequestLayer:
            self.send_error("This is not upload request")
            return None

        if len(self.request.uploadRequestLayer.path) > config.FILE_PATH_MAX_LENGTH:
            self.send_error("The file path cannot be more then {} chars".format(config.FILE_PATH_MAX_LENGTH))
            return None

        if not in_storage(self.request.uploadRequestLayer.path, self._storagePath):
            self.send_error("The path {} is not legal".format(self.request.uploadRequestLayer.path))
            return None

        self.requestID = create_new_requestID()
        res = Pocket(BasicLayer(self.requestID, PocketType.Response, PocketSubType.Upload))
        return (res, None)

    def post_upload(self, data: bytes) -> None:
        # create the file
        assert self.request.uploadRequestLayer
        targetPath = self.get_path(self.request.uploadRequestLayer.path)
        directoyPath = os.path.dirname(targetPath)

        # delete the file / directory if already exists
        if os.path.isfile(targetPath):
            os.remove(targetPath)
        if os.path.isdir(targetPath):
            shutil.rmtree(targetPath)

        if not directoyPath:
            directoyPath = "."
        elif not os.path.isdir(directoyPath):
            os.makedirs(directoyPath, exist_ok=True)

        isFile = struct.unpack_from("?", data)[0]
        data = data[struct.calcsize("?"):]

        if isFile:
            # save the file
            with open(targetPath, "wb") as f:
                f.write(data)
            logging.info('The file "{}" uploaded'.format(self.request.uploadRequestLayer.path))
        else:
            # save the directoy
            zipFile = BytesIO(data)
            with zipfile.ZipFile(zipFile, "r") as zip_archive:
                zip_archive.extractall(targetPath)
            logging.info('The directoy "{}" uploaded'.format(self.request.uploadRequestLayer.path))

class DownloadFileRequestHandler(DownloadRequestHandler):
    def route(self) -> tuple[Pocket, bytes | None] | None:
        # validation
        if not self.request.downloadRequestLayer:
            self.send_error("This is not download request")
            return None

        targetPath = self.get_path(self.request.downloadRequestLayer.path)
        isFile = True
        if not os.path.isfile(targetPath):
            if not os.path.isdir(targetPath):
                self.send_error('The file / directory "{}" dos not exists!'.format(self.request.downloadRequestLayer.path))
                return None
            isFile = False

        if not in_storage(self.request.downloadRequestLayer.path, self._storagePath):
            self.send_error('The file / directory "{}" dos not exists!'.format(self.request.downloadRequestLayer.path))
            return None

        data = struct.pack("?", isFile)

        if isFile:
            # read the file
            with open(targetPath, "rb") as f:
                data += f.read()
        else:
            # read the directory
            archive = BytesIO()
            with zipfile.ZipFile(archive, 'w') as zip_archive:
                for root, dirs, files in os.walk(targetPath):
                    for file in files:
                        fileInfo = zipfile.ZipInfo(os.path.relpath(os.path.join(root, file), os.path.join(targetPath, self.get_path('.'))))
                        with open(os.path.join(root, file), "rb") as f:
                            zip_archive.writestr(fileInfo, f.read())

            archive.seek(0)
            data += archive.read()

        self.requestID = create_new_requestID()
        res = Pocket(BasicLayer(self.requestID, PocketType.Response, PocketSubType.Download))
        return (res, data)


class ListRequestHandler(DownloadRequestHandler):
    def route(self) -> tuple[Pocket, bytes | None] | None:
        # validation
        if not self.request.listRequestLayer:
            self.send_error("This is not list request")
            return None

        directoryPath = self.get_path(self.request.listRequestLayer.path)
        if not os.path.isdir(directoryPath):
            self.send_error('The directory "{}" dos not exists!'.format(self.request.listRequestLayer.path))
            return None

        if not in_storage(self.request.listRequestLayer.path, self._storagePath):
            self.send_error('The directory "{}" dos not exists!'.format(self.request.listRequestLayer.path))
            return None

        # load the content
        data = self.load_directory(directoryPath, "", self.request.listRequestLayer.recursive)

        self.requestID = create_new_requestID()
        res = Pocket(BasicLayer(self.requestID, PocketType.Response, PocketSubType.List))
        return (res, data)

    def load_directory(self, directoryPath: str, parent: str, recursive: bool) -> bytes:
        directoriesAndFiles = os.listdir(directoryPath)
        directories = [directory for directory in directoriesAndFiles if os.path.isdir(directoryPath + "/" + directory)]
        files = [file for file in directoriesAndFiles if os.path.isfile(directoryPath + "/" + file)]

        # soring the directories and files
        directories.sort()
        files.sort()

        # convet to bytes
        data = b""
        for directoryName in directories:
            updatedAt = os.path.getmtime(directoryPath + "/" + directoryName)

            data += pack_directory_block(parent + directoryName, updatedAt)
            if recursive:
                data += self.load_directory(
                    directoryPath + "/" + directoryName, parent + directoryName + "/", recursive
                )

        for fileName in files:
            updatedAt = os.path.getmtime(directoryPath + "/" + fileName)
            fileSize = os.stat(directoryPath + "/" + fileName).st_size

            data += pack_file_block(parent + fileName, updatedAt, fileSize)

        return data
