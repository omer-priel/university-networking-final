# DNS handlers

import socket
import logging
import random
import time

from src.dns.config import config
from src.dns.database import Database, RecordData, save_database, CacheRecord
from src.dns.packets import DNSPacket, DNSQueryRecord, DNSAnswerRecord, str_to_ip, pack_int, unpack_int_from, unpack_host_name, ip_to_str


def request_handler(clientsSocket: socket.socket, parentSocket: socket.socket, database: Database, query: DNSPacket, clientAddress: tuple[str, int]) -> None:
    logging.info("Recived query from client")

    logging.debug(query)

    locals: list[RecordData | None] = [None] * query.queriesCount

    response: DNSPacket | None = None

    # find all the info from this local DNS
    queriesRecords: list[DNSQueryRecord] = []
    i = 0
    missing = query.queriesCount

    for queryRecord in query.queriesRecords:
        recordData = database.get_active_record(queryRecord.domainName)
        if recordData:
            locals[i] = recordData
            missing -= 1
        else:
            queriesRecords += [queryRecord]

        i += 1

    # find if need from the parent DNS
    if missing > 0:
        transactionIDAsNum = unpack_int_from(query.transactionID, 0, 2)[0]
        nextQuery = DNSPacket(pack_int(random.randint(1, transactionIDAsNum - 1), 2), query.flags, len(queriesRecords), 0, 0, 0)
        nextQuery.queriesRecords = queriesRecords

        logging.info("Send query to parent DNS")

        parentSocket.sendto(bytes(nextQuery), (database.parent_dns, 53))
        try:
            data = parentSocket.recvfrom(config.SOCKET_MAXSIZE)[0]

            response = DNSPacket.from_bytes(data)

            logging.info("Recived response from parent DNS")
            logging.debug(response)
        except socket.error:
            pass

    # save the cache
    if response:
        save_cache_into_database(database, response)

    # create the response
    if not response:
        response = DNSPacket(query.transactionID, query.flags, query.queriesCount, 0, 0, 0)

    response.transactionID = query.transactionID
    response.flags.isResponse = True
    response.flags.authoritative = False
    response.flags.recavail = True
    response.flags.authenticated = False
    response.flags.checkdisable = False

    response.queriesCount = query.queriesCount
    response.queriesRecords = query.queriesRecords

    for recordData in locals:
        if recordData:
            response.answersRecords += [DNSAnswerRecord(response, recordData.domain_name, 1, 1, recordData.ttl, str_to_ip(recordData.ip_address))]

    response.answersCount = len(response.answersRecords)

    # send the response

    logging.info("Send response to client")
    logging.debug(response)

    clientsSocket.sendto(bytes(response), clientAddress)


def save_cache_into_database(database: Database, response: DNSPacket):
    now = int(time.time())
    for recod in response.additionalRecords + response.authorityRecords + response.answersRecords:
        if recod.type == 1:  # A
            database.cache_records[recod.domainName] = CacheRecord(ip_address=ip_to_str(recod.rData), expired_time=now + recod.ttl)

    save_database(database)