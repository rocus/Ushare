import logging 
import uuid
import html
import os
import socket
import time
import threading
from aiohttp import web
  
def read_parameters():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", dest="HTTP_PORT" ,   type=int, default=49152)
    parser.add_argument("-o", "--host", dest="SERVER_IP" ,   type=str, default="!0.0.0.100")
    parser.add_argument("-r", "--root", dest="MEDIA_ROOT",   type=str, default="/media/music")
    parser.add_argument("-n", "--name", dest="FRIENDLY_NAME",type=str, default="UshareNG")
    parser.add_argument("-u", "--uuid", dest="UUID",         type=str, default=str(uuid.uuid4()))
    parser.add_argument("-t", "--ttl" , dest="SSDP_TTL",     type=int, default=1800)
    parser.add_argument("-d", "--log" , dest="LOGLEVEL",     choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO")
    return parser.parse_args()

config = read_parameters()

SERVICE_TYPE  = "urn:schemas-upnp-org:service:ContentDirectory:1"
SSDP_ADDR     = "239.255.255.250"
SSDP_PORT     = 1900
URL_BASE      = f"http://{config.SERVER_IP}:{config.HTTP_PORT}/"
LOCATION      = f"{URL_BASE}description.xml"
VERSION       = "1.05"


logging.basicConfig( level=getattr(logging, config.LOGLEVEL), format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

# =========================================================
# GENERAL INFORMATION
# =========================================================

def print_info():
    print(f"{60*'='}                            ")
    print(f"NAME :       {config.FRIENDLY_NAME} ")
    print(f"URL_BASE:    {URL_BASE}             ")
    print(f"MEDIA ROOT:  {config.MEDIA_ROOT}    ")
    print(f"UUID:        {config.UUID}          ")
    print(f"SSDP_TTL:    {config.SSDP_TTL}      ")
    print(f"LOGLEVEL:    {config.LOGLEVEL}      ")
    print(f"Version:     {VERSION}              ")

    count = 0
    for root, dirs, files in os.walk(config.MEDIA_ROOT):
        for name in files:
            if name.lower().endswith((".mp3", ".wma" , ".flac", ".wav" , "ogg" ,".pls",".m3u" , "m3u8" )):
                count += 1 
    print(f"Nr Files:    {count}")
    print(60*"=")


# =========================================================
# FILETYPE DEFINITIONS
# =========================================================

MUSIC    = "object.item.audioItem.musicTrack"
PHOTO    = "object.item.imageItem.photo"
PLAYLIST = "object.item.playlistItem"
FOLDER   = "object.container.storageFolder"

FILE_TYPES = {
    ".mp3" : ("audio/mpeg"      , MUSIC   ),
    ".flac": ("audio/flac"      , MUSIC   ),
    ".wav" : ("audio/wav"       , MUSIC   ),
    ".ogg" : ("audio/ogg"       , MUSIC   ),
    ".wma" : ("audio/x-ms-wma"  , MUSIC   ),
    ".pls" : ("audio/x-scpls"   , PLAYLIST),
    ".m3u" : ("audio/x-mpegurl" , PLAYLIST),
    ".m3u8": ("audio/x-mpegurl" , PLAYLIST),
    ".jpg" : ("image/jpeg"      , PHOTO   ),
    ".jpeg": ("image/jpeg"      , PHOTO   ),
    ".bmp" : ("image/bmp"       , PHOTO   ),
    ".gif" : ("image/gif"       , PHOTO   ),
    ".png" : ("image/png"       , PHOTO   )
}

IGNORED_FILES = ( "Thumbs.db", "desktop.ini", "indexmarks" , ".txt" , ".doc" )

# =========================================================
# GLOBAL REQUEST LOGGING
# =========================================================

@web.middleware
async def log_requests(request, handler):
    if request.remote != "10.0.0.142" and request.remote != "10.0.0.144":
        log.debug(f"\nLOG REQUEST  from {request.remote} : {request.method} {request.raw_path} {request.path} {request.headers}")
    try:
        response = await handler(request)
        if request.remote != "10.0.0.142" and request.remote != "10.0.0.144":
            log.debug(f"\nLOG RESPONSE from {request.remote} : {response.status}")
        return response
    except Exception as e:
        log.error("ERROR:", e)
        raise


# ===============================================================
# SSDP NOTIFY
# ===============================================================

def sssdp_notify():

    msg = "\r\n".join([
        "NOTIFY * HTTP/1.1",
        f"HOST: {SSDP_ADDR}:{SSDP_PORT}",
        f"CACHE-CONTROL: max-age={config.SSDP_TTL}",
        "NT: upnp:rootdevice",
        "NTS: ssdp:alive",

        f"USN: uuid:{config.UUID}::upnp:rootdevice",
        f"LOCATION: {LOCATION}",

        "SERVER: Python UPnP Debug",
        "",
        ""
    ])

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 5)
    sock.sendto(msg.encode(), (SSDP_ADDR, SSDP_PORT))
    sock.close()

def ssdp_notify():

    notifies = [
        ("upnp:rootdevice", f"uuid:{config.UUID}::upnp:rootdevice"),
        (f"uuid:{config.UUID}", f"uuid:{config.UUID}"),
        ("urn:schemas-upnp-org:device:MediaServer:1",
         f"uuid:{config.UUID}::urn:schemas-upnp-org:device:MediaServer:1"),
    ]
    msg=""
    for nt, usn in notifies:
        msg = "\r\n".join([
            "NOTIFY * HTTP/1.1",
            f"HOST: {SSDP_ADDR}:{SSDP_PORT}",
            f"CACHE-CONTROL: max-age={config.SSDP_TTL}",
            f"LOCATION: {LOCATION}",
            f"NT: {nt}",
            "NTS: ssdp:alive",
            f"USN: {usn}",
#            "SERVER: Linux UPnP/1.0 Python/1.0",
            "SERVER: Linux/5.10 UPnP/1.0 DLNADOC/1.50 Python/1.0",
            "",
            ""
        ])
#       log.debug(msg)

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        sock.sendto(msg.encode(), (SSDP_ADDR, SSDP_PORT))


# =========================================================
# SSDP (DISCOVERY)
# =========================================================

def ssdp_loop():
    import datetime
    while True:
        ssdp_notify()
        log.debug("SSDP NOTIFY sent")
        now = datetime.datetime.now()
        log.debug(now.strftime("%Y-%m-%d %H:%M:%S"))
        time.sleep(30)


# =========================================================
# SSDP LISTENER
# =========================================================

def ssdp_listener():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", SSDP_PORT))

    mreq = socket.inet_aton(SSDP_ADDR) + socket.inet_aton("0.0.0.0")
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    log.info("SSDP running")

    while True:
        data, addr = sock.recvfrom(2048)
        msg = data.decode(errors="ignore")

        if "M-SEARCH" not in msg:
            continue
        if addr[0] != "10.0.0.142" and addr[0] != "10.0.0.144" :
            log.debug(f"M-SEARCH from {addr}")
            log.debug(msg)

        st = "upnp:rootdevice"
        for line in msg.splitlines():
            if line.upper().startswith("ST:"):
                st = line.split(":", 1)[1].strip()

        reply = "\r\n".join([
            "HTTP/1.1 200 OK",
            f"CACHE-CONTROL: max-age={config.SSDP_TTL}",
            "EXT:",
            f"LOCATION: {LOCATION}",
            "SERVER: Linux UPnP/1.0 Python",
            f"ST: {st}",
            f"USN: uuid:{config.UUID}::{st}",
            "",
            ""
        ])
        if addr[0] != "10.0.0.142" and addr[0] != "10.0.0.144" :
            log.debug(f"M-SEARCH to {addr}")
            log.debug(reply)

        sock.sendto(reply.encode(), addr)


# =========================================================
# SOAP PARSER 
# =========================================================

def parse_browse(xml_body):
    from xml.etree.ElementTree import fromstring
    try:
        root = fromstring(xml_body)

        body = None
        for el in root:
            if "Body" in el.tag:
                body = el
                break

        if body is None:
            return None, None, None, None

        browse = None
        for el in body:
            if "Browse" in el.tag:
                browse = el
                break

        if browse is None:
            return None, None, None, None

        object_id   = None
        browse_flag = "BrowseDirectChildren"
        start_index = 0
        requested   = 10000

        for el in browse:
            tag = el.tag.split("}")[-1]
            if tag == "ObjectID":
                object_id = el.text
            elif tag == "BrowseFlag":
                browse_flag = el.text
            elif tag == "StartingIndex":
                start_index = int(el.text)
            elif tag == "RequestedCount":
                requested = int(el.text)
        if requested == 0: 
            requested=1000    # SPECIAL CASE


        return object_id, browse_flag , start_index , requested

    except Exception as e:
        log.warning(f"PARSE ERROR: {e}")
        return None, None


#============================================================
# Catch ALL
#============================================================

async def catch_all(request):
    log.warning(f"CATCH ALL \nMETHOD: {request.method} \nPATH: {request.path} \nHEADERS { dict(request.headers)} ")
    body = await request.text()
    log.warning(f"BODY: {body[:500]}")


    soapaction = request.headers.get("SOAPACTION", "")

    log.warning(f"SOAPACTION: {soapaction}")

    if "ContentDirectory:1" in soapaction:
        log.warning("Dispatching to cds_control")
        return await cds_control(request)

    elif "ConnectionManager:1" in soapaction:
        log.warning("Dispatching to cms_control")
        return await cms_control(request)

    elif "X_MS_MediaReceiverRegistrar:1" in soapaction:
        log.warning("Dispatching to msr_control")
        return await msr_control(request)

    return web.Response(status=404)


# =========================================================
# DESCRIPTION.XML
# =========================================================

async def description(request):
    log.debug(f"DESCRIPTION.XML requested {request}")
    xml = f"""<?xml version="1.0"?>
<root xmlns="urn:schemas-upnp-org:device-1-0">
   <specVersion>
      <major>1</major>
      <minor>0</minor>
   </specVersion>
   <device>
      <deviceType>urn:schemas-upnp-org:device:MediaServer:1</deviceType>
      <friendlyName>{config.FRIENDLY_NAME}</friendlyName>
      <manufacturer>GeeXboX Team</manufacturer>
      <manufacturerURL>http://ushare.geexbox.org/</manufacturerURL>
      <modelDescription>GeeXboX uShare : UPnP Media Server</modelDescription>
      <modelName>uShare</modelName>
      <modelNumber>001</modelNumber>
      <modelURL>http://ushare.geexbox.org/</modelURL>
      <serialNumber>GEEXBOX-USHARE-02</serialNumber>
      <UDN>uuid:{config.UUID}</UDN>
      <presentationURL>/web/ushare.html</presentationURL>
      <iconList>
         <icon>
            <mimetype>image/png</mimetype>
            <width>48</width>
            <height>48</height>
            <depth>24</depth>
            <url>/ushareng.png</url>
         </icon>
         <icon>
            <mimetype>image/png</mimetype>
            <width>120</width>
            <height>120</height>
            <depth>24</depth>
            <url>/ushareng.png</url>
         </icon>
      </iconList>
      <serviceList>
         <service>
            <serviceType>urn:schemas-upnp-org:service:ConnectionManager:1</serviceType>
            <serviceId>urn:upnp-org:serviceId:ConnectionManager</serviceId>
            <SCPDURL>/web/cms.xml</SCPDURL>
            <controlURL>/web/cms_control</controlURL>
            <eventSubURL>/web/cms_event</eventSubURL>
         </service>
         <service>
            <serviceType>urn:schemas-upnp-org:service:ContentDirectory:1</serviceType>
            <serviceId>urn:upnp-org:serviceId:ContentDirectory</serviceId>
            <SCPDURL>/web/cds.xml</SCPDURL>
            <controlURL>/web/cds_control</controlURL>
            <eventSubURL>/web/cds_event</eventSubURL>
         </service>
         <service>
            <serviceType>urn:microsoft.com:service:X_MS_MediaReceiverRegistrar:1</serviceType>
            <serviceId>urn:microsoft.com:serviceId:X_MS_MediaReceiverRegistrar</serviceId>
            <SCPDURL>/web/msr.xml</SCPDURL>
            <controlURL>/web/msr_control</controlURL>
            <eventSubURL>/web/msr_event</eventSubURL>
         </service>
      </serviceList>
   </device>
   <URLBase>{URL_BASE}</URLBase>
</root>
"""

    lines = xml.splitlines()
    xml = "\r\n".join(lines) + "\r\n"
    headers = {
        "CONTENT-TYPE": "text/xml",
        "DATE": "Sun, 07 Jun 2026 11:52:33 GMT",
        "LAST-MODIFIED": "Mon, 08 Sep 2025 16:41:07 GMT",
        "SERVER": "Linux/5.4.72+, UPnP/1.0, Portable SDK for UPnP devices/1.4.2",
        "X-User-Agent": "redsonic",
        "CONNECTION": "close",
    }

    return web.Response( body=xml.encode("utf-8"), headers=headers)


# ==================================================
# MSR XML
# ==================================================

async def msr_xml(request):
    log.debug(f"MSR.XML requested {request}")
    xml = """<?xml version="1.0" encoding="utf-8"?>
<scpd>
   <specVersion>
      <major>1</major>
      <minor>0</minor>
   </specVersion>
   <actionList>
      <action>
         <name>IsAuthorized</name>
         <argumentList>
            <argument>
               <name>DeviceID</name>
               <direction>in</direction>
               <relatedStateVariable>A_ARG_TYPE_DeviceID</relatedStateVariable>
            </argument>
            <argument>
               <name>Result</name>
               <direction>out</direction>
               <relatedStateVariable>A_ARG_TYPE_Result</relatedStateVariable>
            </argument>
         </argumentList>
      </action>
      <action>
         <name>RegisterDevice</name>
         <argumentList>
            <argument>
               <name>RegistrationReqMsg</name>
               <direction>in</direction>
               <relatedStateVariable>A_ARG_TYPE_RegistrationReqMsg</relatedStateVariable>
            </argument>
            <argument>
               <name>RegistrationRespMsg</name>
               <direction>out</direction>
               <relatedStateVariable>A_ARG_TYPE_RegistrationRespMsg</relatedStateVariable>
            </argument>
         </argumentList>
      </action>
      <action>
         <name>IsValidated</name>
         <argumentList>
            <argument>
               <name>DeviceID</name>
               <direction>in</direction>
               <relatedStateVariable>A_ARG_TYPE_DeviceID</relatedStateVariable>
            </argument>
            <argument>
               <name>Result</name>
               <direction>out</direction>
               <relatedStateVariable>A_ARG_TYPE_Result</relatedStateVariable>
            </argument>
         </argumentList>
      </action>
   </actionList>
   <serviceStateTable>
      <stateVariable sendEvents="no">
         <name>A_ARG_TYPE_DeviceID</name>
         <dataType>string</dataType>
      </stateVariable>
      <stateVariable sendEvents="no">
         <name>A_ARG_TYPE_Result</name>
         <dataType>int</dataType>
      </stateVariable>
      <stateVariable sendEvents="no">
         <name>A_ARG_TYPE_RegistrationReqMsg</name>
         <dataType>bin.base64</dataType>
      </stateVariable>
      <stateVariable sendEvents="no">
         <name>A_ARG_TYPE_RegistrationRespMsg</name>
         <dataType>bin.base64</dataType>
      </stateVariable>
      <stateVariable sendEvents="no">
         <name>AuthorizationGrantedUpdateID</name>
         <dataType>ui4</dataType>
      </stateVariable>
      <stateVariable sendEvents="no">
         <name>AuthorizationDeniedUpdateID</name>
         <dataType>ui4</dataType>
      </stateVariable>
      <stateVariable sendEvents="no">
         <name>ValidationSucceededUpdateID</name>
         <dataType>ui4</dataType>
      </stateVariable>
      <stateVariable sendEvents="no">
         <name>ValidationRevokedUpdateID</name>
         <dataType>ui4</dataType>
      </stateVariable>
   </serviceStateTable>
</scpd>"""
    return web.Response(text=xml, content_type="text/xml")


#=========================================================
# MSR CONTROL
#=========================================================

async def msr_control(request):
    log.debug(f"MSR_CONTROL requested {request}")
    body = await request.text()
    xml = """<?xml version="1.0"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
<s:Body>
<u:IsAuthorizedResponse xmlns:u="urn:microsoft.com:service:X_MS_MediaReceiverRegistrar:1">
<Result>1</Result>      
</u:IsAuthorizedResponse>
</s:Body>
</s:Envelope>"""
    return web.Response( text=xml, content_type="text/xml") 


#=========================================================
# MSR EVENTING
#=========================================================
            
async def msr_event(request):
    log.debug("MSR EVENT ")
    sid = "uuid:" + config.UUID
    headers = {
        "SID": sid,
        "TIMEOUT": "Second-1800"
    }       
    return web.Response(status=200, headers=headers)


# ==================================================
# CMS XML
# ==================================================

async def cms_xml(request):
    log.debug(f"CMS.XML requested {request}")
    xml = """<?xml version="1.0" encoding="utf-8"?>
<scpd xmlns="urn:schemas-upnp-org:service-1-0">
   <specVersion>
      <major>1</major>
      <minor>0</minor>
   </specVersion>
   <actionList>
      <action>
         <name>GetCurrentConnectionInfo</name>
         <argumentList>
            <argument>
               <name>ConnectionID</name>
               <direction>in</direction>
               <relatedStateVariable>A_ARG_TYPE_ConnectionID</relatedStateVariable>
            </argument>
            <argument>
               <name>RcsID</name>
               <direction>out</direction>
               <relatedStateVariable>A_ARG_TYPE_RcsID</relatedStateVariable>
            </argument>
            <argument>
               <name>AVTransportID</name>
               <direction>out</direction>
               <relatedStateVariable>A_ARG_TYPE_AVTransportID</relatedStateVariable>
            </argument>
            <argument>
               <name>ProtocolInfo</name>
               <direction>out</direction>
               <relatedStateVariable>A_ARG_TYPE_ProtocolInfo</relatedStateVariable>
            </argument>
            <argument>
               <name>PeerConnectionManager</name>
               <direction>out</direction>
               <relatedStateVariable>A_ARG_TYPE_ConnectionManager</relatedStateVariable>
            </argument>
            <argument>
               <name>PeerConnectionID</name>
               <direction>out</direction>
               <relatedStateVariable>A_ARG_TYPE_ConnectionID</relatedStateVariable>
            </argument>
            <argument>
               <name>Direction</name>
               <direction>out</direction>
               <relatedStateVariable>A_ARG_TYPE_Direction</relatedStateVariable>
            </argument>
            <argument>
               <name>Status</name>
               <direction>out</direction>
               <relatedStateVariable>A_ARG_TYPE_ConnectionStatus</relatedStateVariable>
            </argument>
         </argumentList>
      </action>
      <action>
         <name>GetProtocolInfo</name>
         <argumentList>
            <argument>
               <name>Source</name>
               <direction>out</direction>
               <relatedStateVariable>SourceProtocolInfo</relatedStateVariable>
            </argument>
            <argument>
               <name>Sink</name>
               <direction>out</direction>
               <relatedStateVariable>SinkProtocolInfo</relatedStateVariable>
            </argument>
         </argumentList>
      </action>
      <action>
         <name>GetCurrentConnectionIDs</name>
         <argumentList>
            <argument>
               <name>ConnectionIDs</name>
               <direction>out</direction>
               <relatedStateVariable>CurrentConnectionIDs</relatedStateVariable>
            </argument>
         </argumentList>
      </action>
   </actionList>
   <serviceStateTable>
      <stateVariable sendEvents="no">
         <name>A_ARG_TYPE_ProtocolInfo</name>
         <dataType>string</dataType>
      </stateVariable>
      <stateVariable sendEvents="no">
         <name>A_ARG_TYPE_ConnectionStatus</name>
         <dataType>string</dataType>
         <allowedValueList>
            <allowedValue>OK</allowedValue>
            <allowedValue>ContentFormatMismatch</allowedValue>
            <allowedValue>InsufficientBandwidth</allowedValue>
            <allowedValue>UnreliableChannel</allowedValue>
            <allowedValue>Unknown</allowedValue>
         </allowedValueList>
      </stateVariable>
      <stateVariable sendEvents="no">
         <name>A_ARG_TYPE_AVTransportID</name>
         <dataType>i4</dataType>
      </stateVariable>
      <stateVariable sendEvents="no">
         <name>A_ARG_TYPE_RcsID</name>
         <dataType>i4</dataType>
      </stateVariable>
      <stateVariable sendEvents="no">
         <name>A_ARG_TYPE_ConnectionID</name>
         <dataType>i4</dataType>
      </stateVariable>
      <stateVariable sendEvents="no">
         <name>A_ARG_TYPE_ConnectionManager</name>
         <dataType>string</dataType>
      </stateVariable>
      <stateVariable sendEvents="yes">
         <name>SourceProtocolInfo</name>
         <dataType>string</dataType>
      </stateVariable>
      <stateVariable sendEvents="yes">
         <name>SinkProtocolInfo</name>
         <dataType>string</dataType>
      </stateVariable>
      <stateVariable sendEvents="no">
         <name>A_ARG_TYPE_Direction</name>
         <dataType>string</dataType>
         <allowedValueList>
            <allowedValue>Input</allowedValue>
            <allowedValue>Output</allowedValue>
         </allowedValueList>
      </stateVariable>
      <stateVariable sendEvents="yes">
         <name>CurrentConnectionIDs</name>
         <dataType>string</dataType>
      </stateVariable>
   </serviceStateTable>
</scpd>"""
    return web.Response(text=xml, content_type="text/xml")


#=========================================================
# CMS CONTROL
#=========================================================

async def cms_control(request):
    log.debug("CMS CONTROL")
    body = await request.text()
    log.debug(body)
    return web.Response(text="soap_ok",
                        content_type="text/xml")


#=========================================================
# CMS EVENT
#=========================================================

async def cms_event(request):
    log.debug("CMS EVENT ")
    sid = "uuid:" + config.UUID
    headers = {
        "SID": sid,
        "TIMEOUT": "Second-1800"
    }
    return web.Response(status=200, headers=headers)


# =========================================================
# CDS XML (SERVICE DEFINITION)
# =========================================================

async def cds_xml(request):
    log.debug(f"CDS.XML requested {request}")
    xml = f"""<?xml version="1.0" encoding="utf-8"?>
<scpd xmlns="urn:schemas-upnp-org:service-1-0">
   <specVersion>
      <major>1</major>
      <minor>0</minor>
   </specVersion>
   <actionList>
      <action>
         <name>Browse</name>
         <argumentList>
            <argument>
               <name>ObjectID</name>
               <direction>in</direction>
               <relatedStateVariable>A_ARG_TYPE_ObjectID</relatedStateVariable>
            </argument>
            <argument>
               <name>BrowseFlag</name>
               <direction>in</direction>
               <relatedStateVariable>A_ARG_TYPE_BrowseFlag</relatedStateVariable>
            </argument>
            <argument>
               <name>Filter</name>
               <direction>in</direction>
               <relatedStateVariable>A_ARG_TYPE_Filter</relatedStateVariable>
            </argument>
            <argument>
               <name>StartingIndex</name>
               <direction>in</direction>
               <relatedStateVariable>A_ARG_TYPE_Index</relatedStateVariable>
            </argument>
            <argument>
               <name>RequestedCount</name>
               <direction>in</direction>
               <relatedStateVariable>A_ARG_TYPE_Count</relatedStateVariable>
            </argument>
            <argument>
               <name>SortCriteria</name>
               <direction>in</direction>
               <relatedStateVariable>A_ARG_TYPE_SortCriteria</relatedStateVariable>
            </argument>
            <argument>
               <name>Result</name>
               <direction>out</direction>
               <relatedStateVariable>A_ARG_TYPE_Result</relatedStateVariable>
            </argument>
            <argument>
               <name>NumberReturned</name>
               <direction>out</direction>
               <relatedStateVariable>A_ARG_TYPE_Count</relatedStateVariable>
            </argument>
            <argument>
               <name>TotalMatches</name>
               <direction>out</direction>
               <relatedStateVariable>A_ARG_TYPE_Count</relatedStateVariable>
            </argument>
            <argument>
               <name>UpdateID</name>
               <direction>out</direction>
               <relatedStateVariable>A_ARG_TYPE_UpdateID</relatedStateVariable>
            </argument>
         </argumentList>
      </action>
      <action>
         <name>DestroyObject</name>
         <argumentList>
            <argument>
               <name>ObjectID</name>
               <direction>in</direction>
               <relatedStateVariable>A_ARG_TYPE_ObjectID</relatedStateVariable>
            </argument>
         </argumentList>
      </action>
      <action>
         <name>GetSystemUpdateID</name>
         <argumentList>
            <argument>
               <name>Id</name>
               <direction>out</direction>
               <relatedStateVariable>SystemUpdateID</relatedStateVariable>
            </argument>
         </argumentList>
      </action>
      <action>
         <name>GetSearchCapabilities</name>
         <argumentList>
            <argument>
               <name>SearchCaps</name>
               <direction>out</direction>
               <relatedStateVariable>SearchCapabilities</relatedStateVariable>
            </argument>
         </argumentList>
      </action>
      <action>
         <name>GetSortCapabilities</name>
         <argumentList>
            <argument>
               <name>SortCaps</name>
               <direction>out</direction>
               <relatedStateVariable>SortCapabilities</relatedStateVariable>
            </argument>
         </argumentList>
      </action>
      <action>
         <name>UpdateObject</name>
         <argumentList>
            <argument>
               <name>ObjectID</name>
               <direction>in</direction>
               <relatedStateVariable>A_ARG_TYPE_ObjectID</relatedStateVariable>
            </argument>
            <argument>
               <name>CurrentTagValue</name>
               <direction>in</direction>
               <relatedStateVariable>A_ARG_TYPE_TagValueList</relatedStateVariable>
            </argument>
            <argument>
               <name>NewTagValue</name>
               <direction>in</direction>
               <relatedStateVariable>A_ARG_TYPE_TagValueList</relatedStateVariable>
            </argument>
         </argumentList>
      </action>
   </actionList>
   <serviceStateTable>
      <stateVariable sendEvents="no">
         <name>A_ARG_TYPE_BrowseFlag</name>
         <dataType>string</dataType>
         <allowedValueList>
            <allowedValue>BrowseMetadata</allowedValue>
            <allowedValue>BrowseDirectChildren</allowedValue>
         </allowedValueList>
      </stateVariable>
      <stateVariable sendEvents="yes">
         <name>SystemUpdateID</name>
         <dataType>ui4</dataType>
      </stateVariable>
      <stateVariable sendEvents="no">
         <name>A_ARG_TYPE_Count</name>
         <dataType>ui4</dataType>
      </stateVariable>
      <stateVariable sendEvents="no">
         <name>A_ARG_TYPE_SortCriteria</name>
         <dataType>string</dataType>
      </stateVariable>
      <stateVariable sendEvents="no">
         <name>SortCapabilities</name>
         <dataType>string</dataType>
      </stateVariable>
      <stateVariable sendEvents="no">
         <name>A_ARG_TYPE_Index</name>
         <dataType>ui4</dataType>
      </stateVariable>
      <stateVariable sendEvents="no">
         <name>A_ARG_TYPE_ObjectID</name>
         <dataType>string</dataType>
      </stateVariable>
      <stateVariable sendEvents="no">
         <name>A_ARG_TYPE_UpdateID</name>
         <dataType>ui4</dataType>
      </stateVariable>
      <stateVariable sendEvents="no">
         <name>A_ARG_TYPE_TagValueList</name>
         <dataType>string</dataType>
      </stateVariable>
      <stateVariable sendEvents="no">
         <name>A_ARG_TYPE_Result</name>
         <dataType>string</dataType>
      </stateVariable>
      <stateVariable sendEvents="no">
         <name>SearchCapabilities</name>
         <dataType>string</dataType>
      </stateVariable>
      <stateVariable sendEvents="no">
         <name>A_ARG_TYPE_Filter</name>
         <dataType>string</dataType>
      </stateVariable>
   </serviceStateTable>
</scpd>"""
    return web.Response(text=xml, content_type="text/xml")


# =========================================================
# BROWSE HANDLER (CORE FUNCTION)
# =========================================================

def normalize_object_id(object_id):
    if object_id is None:
        return "0"

    object_id = object_id.strip()

    if object_id == "":
        return "0"

    return object_id


# ---------------------------------------------------------
# OBJECT ID → FILESYSTEM PATH
# ---------------------------------------------------------

def get_path(object_id):
    object_id = normalize_object_id(object_id)
    if object_id == "0":
        return config.MEDIA_ROOT
    return os.path.join(config.MEDIA_ROOT, object_id)


# ---------------------------------------------------------
# LIST DIRECTORY AND FILES
# ---------------------------------------------------------

def list_directory(object_id):
    path = get_path(object_id)
    if os.path.isdir (path):
        sortedlist = sorted((f for f in os.listdir(path) if not f.startswith(".")), key=str.lower)
    else:
        sortedlist = [os.path.basename (path)] 
        path = os.path.dirname (path) 
        object_id = os.path.dirname (object_id )  
    items = []
    log.info (f"Directory  {path}")
    log.debug(f"sorted list {sortedlist}")
    log.info (f"Listed directory length: {len(sortedlist)}")

    try:
        for entry in sortedlist:
            full = os.path.join(path, entry)
            child_id = f"{object_id}/{entry}" if object_id not in ("0", None, "") else entry
            log.debug(f"FULL:  {full} ENTRY: {entry} ISFILE: {os.path.isfile(full)} ISDIR: {os.path.isdir(full)}")

            # ------------------------
            # DIRECTORY
            # ------------------------
            if os.path.isdir(full):
                items.append({
                    "id"    : child_id,
                    "title" : entry,
                    "class" : FOLDER,
                    "file"  : full
                })
            # ------------------------
            # FILE 
            # ------------------------
            elif full.endswith ( IGNORED_FILES ):
                pass
            elif os.path.isfile(full):
                ext  = os.path.splitext(entry)[1].lower()
                try:
                    mime, upnp_class = FILE_TYPES[ext]
                    items.append({
                        "id"    : child_id,
                        "title" : entry,
                        "class" : upnp_class,
                        "file"  : full,
                        "mime"  : mime
                    })
                except KeyError:
                    log.warning("UNKNOWN FILE TYPE: "+ full)
            else:
                log.error("NOT A FILE OR DIRECTORY?" + full)
    except Exception as e:
        log.error("Filesystem error:"+ e)
    log.info(f"Valid items {len(items)}")
    return items


# ---------------------------------------------------------
# BUILD DIDL-LITE XML
# ---------------------------------------------------------

def xml_escape(s: str) -> str:
    return (s
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;"))

def build_didl(items, parent_id, request_host):
    xml = """
<DIDL-Lite xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/"
           xmlns:dc="http://purl.org/dc/elements/1.1/"
           xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/">
"""

    safe_parent_id = xml_escape (parent_id)
    for it in items:
        from urllib.parse import quote
        it_class = it ["class"] 
        it_id    = xml_escape( it["id"] )
        it_title = xml_escape( it['title'])
        url_path = quote(it["id"], safe="/")
        res_url  = f"http://{request_host}/media/{url_path}"

        # ------------------------
        # FOLDER
        # ------------------------
        if it_class == FOLDER:
            log.debug(f"RESURL Directory {res_url}")
            child_count = len(os.listdir(it["file"]))
            xml += f"""   <container id="{it_id}" parentID="{safe_parent_id}" restricted="0" childCount="{child_count}">
      <dc:title>{it_title}</dc:title>
      <upnp:class>{it_class}</upnp:class>
   </container> 
"""

        # ------------------------
        # FILE
        # ------------------------
        elif it_class in (MUSIC, PLAYLIST, PHOTO):
            log.debug(f"RESURL FILE {res_url}")

            ins_size = ""
            ins_tags = ""
            if it_class == MUSIC:
                from mutagen.easyid3 import EasyID3
                from mutagen.id3 import ID3NoHeaderError
                title    = ""
                artist   = ""
                album    = ""
                try:
                    audio  = EasyID3(it["file"])
                    title  = xml_escape(audio.get("title",  [it_title])[0])
                    artist = xml_escape(audio.get("artist", [""])[0])
                    album  = xml_escape(audio.get("album",  [""])[0])
                except ID3NoHeaderError:
                    pass
                ins_size = f""" size="{os.path.getsize(it['file'])}" """ 
                ins_tags = f"""<upnp:title>{title}</upnp:title>
      <upnp:artist>{artist}</upnp:artist>
      <upnp:album>{album}</upnp:album> """

            xml += f"""   <item id="{it_id}" parentID="{safe_parent_id}" restricted="1">
      <dc:title>{it_title}</dc:title>
      <upnp:class>{it_class}</upnp:class>
      {ins_tags}
      <res protocolInfo="http-get:*:{it['mime']}:*" {ins_size}>{res_url}</res>
   </item> 
"""
        else:
            log.error( "THIS SHOULD NOT HAPPEN")

    xml += "</DIDL-Lite>"
    log.debug("DIDL XML\n"+xml)
    return xml


# ---------------------------------------------------------
#  CDS CONTROL
# ---------------------------------------------------------

async def cds_control_getsearch(request,body):
    log.debug("CDS CONTROL GETSEARCH")
    soap = """<?xml version="1.0"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
  <s:Body>
    <u:GetSearchCapabilitiesResponse
        xmlns:u="urn:schemas-upnp-org:service:ContentDirectory:1">
       <SearchCaps>
       </SearchCaps>
    </u:GetSearchCapabilitiesResponse>
  </s:Body>
</s:Envelope>"""
    return web.Response(text=soap, content_type="text/xml")

async def cds_control_getsort(request, body):
    log.debug("CDS CONTROL GETSORT")
    soap = """<?xml version="1.0"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
  <s:Body>
    <u:GetSortCapabilitiesResponse
        xmlns:u="urn:schemas-upnp-org:service:ContentDirectory:1">
      <SortCaps>
      </SortCaps>
    </u:GetSortCapabilitiesResponse>
  </s:Body>
</s:Envelope>"""
    return web.Response(text=soap, content_type="text/xml")

async def cds_control_browse(request, body):  
    log.debug("CDS CONTROL BROWSE")
    object_id, browse_flag , start_index , requested = parse_browse(body)
    request_host = request.host
    log.debug(f"Request host:{request_host} , Object_id: {object_id} , start_index: {start_index} , requested: {requested}, Browseflag:  { browse_flag}" )
    items = list_directory(object_id)
    total_matches = len(items)
    if start_index != None and requested != None:
         items = items [start_index : start_index + requested]
    didl = build_didl(items, object_id, request.host)
    log.info(f"Returned items: {len(items)}")
    safe_didl = html.escape(didl)
    number_returned = len(items)

    soap2 = f"""<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"
            xmlns:u="urn:schemas-upnp-org:service:ContentDirectory:1">
  <s:Body>
    <u:BrowseResponse>
      <Result>{safe_didl}</Result>
      <NumberReturned>{number_returned}</NumberReturned>
      <TotalMatches>{total_matches}</TotalMatches>
      <UpdateID>1</UpdateID>
    </u:BrowseResponse>
  </s:Body>
</s:Envelope>"""

    soap = f'''<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"
            s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <s:Body>
    <u:BrowseResponse xmlns:u="urn:schemas-upnp-org:service:ContentDirectory:1">
      <Result>{safe_didl}</Result>
      <NumberReturned>{number_returned}</NumberReturned>
      <TotalMatches>{total_matches}</TotalMatches>
      <UpdateID>1</UpdateID>
    </u:BrowseResponse>
  </s:Body>
</s:Envelope>'''

    return web.Response(
        text=soap,
        content_type="text/xml",
        charset="utf-8"
    )

async def cds_control(request):
    log.debug("CDS CONTROL")
    body = await request.text()
    action = request.headers.get("SOAPACTION")
    log.debug(f"ACTION {action}")
    if "Browse" in action:
        return await cds_control_browse(request,body)
    elif "GetSearchCapabilities" in action:
        return await cds_control_getsearch(request,body)
    elif "GetSortCapabilities" in action:
        return await cds_control_getsort(request,body)
    return web.Response(status=500)

# =========================================================
# CDS EVENTING 
# =========================================================
"""
async def cds_event(request):
    log.debug(f"CDS EVENT: {request.method}")

    return web.Response(
        status=200,
        headers={
            "SID": f"uuid:{uuid.uuid4()}",
            "TIMEOUT": "Second-1800",
        }
    )
"""
subscriptions = {}

async def cds_event(request):
    log.debug("CDS EVENT")
    body = await request.text()
    sid  = request.headers.get("SID")
    log.debug(f"SID {sid}")

    for i in subscriptions:
        log.debug(f"SUBSCRIPTIONS { i}  {subscriptions[i]}")
    now = time.time()
    for i in list(subscriptions):
        if subscriptions[i]["expires"] < now:
            log.debug(f"EXPIRED SUBSCRIPTION DELETED {i}" )
            del subscriptions[i]
    if request.method == "UNSUBSCRIBE":
        sid = request.headers.get("SID")

        if sid in subscriptions:
            del subscriptions[sid]
            log.debug(f"UNSUBSCRIBE {sid}")
        return web.Response(status=200)
    elif request.method == "SUBSCRIBE":
        if sid:
            if sid not in subscriptions:
                log.debug(f"SUBSCRIPTION ERROR {sid}  {request.method}")
                return web.Response(status=412)

            subscriptions[sid]["expires"] = time.time() + 1800
            log.debug(f"RENEWAL {sid}" )
            return web.Response(
                status=200,
                headers={
                    "SID": sid,
                    "TIMEOUT": "Second-1800"
                }
            )

        sid = f"uuid:{uuid.uuid4()}"
        subscriptions[sid] = {
            "callback": request.headers.get("CALLBACK"),
            "expires": time.time() + 1800
        }
        log.debug(f"NEW SUBSCRIPTION {sid}" )
        return web.Response(
            status=200,
            headers={
                "SID": sid,
                "TIMEOUT": "Second-1800"
            }
        )

# =========================================================
# MEDIA HANDLER
# =========================================================

async def mmmedia_handler(request):
    rel_path = request.match_info["path"]
    full_path = os.path.join(config.MEDIA_ROOT, rel_path)

    log.info(f"STREAM: { full_path}")

    if not os.path.exists(full_path):
        return web.Response(status=404)

    return web.FileResponse(
        full_path,
        headers={
            "Content-Type": "audio/mpeg",
        },
    )

async def mmedia_handler(request):
    rel_path = request.match_info["path"]
    full_path = os.path.join(config.MEDIA_ROOT, rel_path)

    log.info(f"Streaming: { full_path}")

    if not os.path.exists(full_path):
        return web.Response(status=404)

    return web.FileResponse(full_path)


async def media_handler(request):
    rel_path = request.match_info["path"]
    full_path = os.path.join(config.MEDIA_ROOT, rel_path)

    log.info("STREAM:"+ full_path)

    if not os.path.exists(full_path):
        return web.Response(status=404)

    range_header = request.headers.get("Range")
    log.info(f"RANGE HEADER {range_header}")

    if range_header:
        start = int(range_header.replace("bytes=", "").split("-")[0])
        file_size = os.path.getsize(full_path)
        f = open(full_path, "rb")
        f.seek(start)

        data = f.read()
        log.info(f"LENGHT { len (data)}")

        return web.Response(
            status=206,
            body=data,
            headers={
                "Content-Type": "audio/mpeg",
                "Content-Length": str(len(data)),
                "Content-Range": f"bytes {start}-{file_size-1}/{file_size}",
                "Accept-Ranges": "bytes",
            },
        )

    return web.FileResponse(
        full_path,
        headers={
            "Content-Type": "audio/mpeg",
            "Accept-Ranges": "bytes",
        },
    )

# =========================================================
# ICON HANDLER
# =========================================================
import base64

icon_b64= """
iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAC9UlEQVR4AWNAB4xMKkCsz8gj5cLAI+XK
ENG4lUE7dIK+VuhEG2GHRnYJ9w4G7EAulYFBJo1hwqpTDAkNa7wCixf7WyfNsPz//z+Dbcqs/tjale+d
M+fN1AmfpBbZvJNB0KoMVX/7goMM6a3r7Som7yzP69220b94yTynrHnNuy+/YLBPnTWloGPt/4jSBf8t
E6ZdNoqZ5goyWMy6CqJZPaAbTMfXr47KbN+4NL1j8x2vwiW3LZNnbVML6guySJg+zTV12n/LyJ7/uoEd
/81ip941iJ5qbJYwE2KAqn8XA4NEMhPQgIDklg1bQqtW3XbInH8HqGiZamBvtGnc9Kl6wd3/tfzb/xuE
dP93Tp353yV7wQwGBgMmuBfEnRoZFh+6z+Cas6DeLm3OPOvUORt1IyeXKft121skzZpkkTDjh1XijGf+
hYt/FHRv/p/QtP6EgEOTINwABa92oFNyGI2jp1joR0zyM4ia7OOat5jhLSgQ0+dPt0mfv1w7bKKKTdrc
uOoZ+16UTt5zksW0ShAzNgRMGHg0IhkYZf0ZxSxyGbY8AhqQsWAGCK+8/o8BFHjRDRumxjdvWsrAwMyM
I04Rrtr6FGTAwhkgvPfNfwbH7EUMRrHT8oABmOySt5SBINj/CWhA5sIZdpmLZhz6/B9kKAi7yXu2yYPY
GEDWvYWBz7KCSSd8sr1l4qyJ5nHTJwD9f8w2c9G0Q1/gBrACMSOGAWL2dWDaKHZ6bFbnlldLt13475Ey
/b+hT9t/q/iZU1dsuAs2ACfQj5zCoBcxWdMyZd69joVH//cvPvxf36Pxv5lP13/7lAVtJX0nGRS9secF
RiBmAWJmw4j+BKOoqf90A3v/qznX/Tfz7vrvlbXyhV5gsytQngOIOYGYDaQWrA9KsAOxMBBLK9qlhhsF
d7/Vc2v8bxc+9Z9X9sqHer5VxUA5TSBWA2JlkDog5oNYirCdF4hFmLmEZLW8a5Itoicvso6f1qNomwKy
WQ6KZYBYAoiFoC5hBgBbOyAL5dtgQwAAAABJRU5ErkJggg=="""

body = base64.b64decode(icon_b64)

async def icon_handler(request):
    return web.Response( body=body,content_type="image/png")
 
# =========================================================
# APP and RUN
# =========================================================

def run():
#   app = web.Application(middlewares=[log_requests])
    app = web.Application()   # Without logging

    app.router.add_get("/description.xml", description)
    app.router.add_get("/web/cms.xml", cms_xml)
    app.router.add_post("/web/cms_control", cms_control)
    app.router.add_route("*", "/web/cms_event", cms_event)
    app.router.add_get("/web/cds.xml", cds_xml)
    app.router.add_post("/web/cds_control", cds_control)
    app.router.add_route("*", "/web/cds_event", cds_event)
    app.router.add_get("/web/msr.xml", msr_xml)
    app.router.add_post("/web/msr_control", msr_control)
    app.router.add_route("*", "/web/msr_event", msr_event)

    app.router.add_route("*", "/{tail:.*}" , catch_all)

    app.router.add_get("/ushareng.png"   , icon_handler)    
    app.router.add_get("/favicon.ico"    , icon_handler)
    app.router.add_get("/media/{path:.*}", media_handler)
    web.run_app(app, host="0.0.0.0", port=config.HTTP_PORT,access_log=None,print=None)

if __name__ == "__main__":
    print_info()
    threading.Thread(target=ssdp_loop,     daemon=True).start()
    threading.Thread(target=ssdp_listener, daemon=True).start()
    run()
