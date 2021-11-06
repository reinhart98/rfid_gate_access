import RPi.GPIO as GPIO
import MFRC522
#from mfrc522 import MFRC522
import signal, ast
import datetime
MIFAREReader = MFRC522.MFRC522()

# Capture SIGINT for cleanup when the script is aborted
def end_read(signal,frame):
    global continue_reading
    print("Ctrl+C captured, ending read.")
    continue_reading = False
    GPIO.cleanup()

# Hook the SIGINT
signal.signal(signal.SIGINT, end_read)

class readRFID:
    def __init__(self):
        # Create an object of the class MFRC522
        
        self.sectorNama = 2
        self.sectorUsername = 4
        self.sectorNik = 6
        self.sectorDivisi = 8
        self.sectorAccess = 9
    
    def checkIfRFIDTab(self):
        
        returndata = ""
        (status,TagType) = MIFAREReader.MFRC522_Request(MIFAREReader.PICC_REQIDL)

        # If a card is found
        if status == MIFAREReader.MI_OK:
            print("Card detected")
        
        # Get the UID of the card
        (status,uid) = MIFAREReader.MFRC522_Anticoll()

        # If we have the UID, continue
        if status == MIFAREReader.MI_OK:

            # Print UID
            print("Card read UID: %s,%s,%s,%s" % (uid[0], uid[1], uid[2], uid[3]))
        
            # This is the default key for authentication
            key = [0xFF,0xFF,0xFF,0xFF,0xFF,0xFF]
            
            return True,uid,key
        else:
            return False
                
        
    
    def readSector(self,secName="uuid"):
        t1 = datetime.datetime.now()
        continue_reading = True
        datas = ""
        blockAddr = 0
        if(secName == 'nama'):
            blockAddr = self.sectorNama
        elif(secName == 'username'):
            blockAddr = self.sectorUsername
        elif(secName == 'nik'):
            blockAddr = self.sectorNik
        elif(secName == 'divisi'):
            blockAddr = self.sectorDivisi
        elif(secName == 'access'):
            blockAddr = self.sectorAccess
        else:
            blockAddr = 0
        while continue_reading:
            t2 = datetime.datetime.now()
            # Scan for cards    
            (status,TagType) = MIFAREReader.MFRC522_Request(MIFAREReader.PICC_REQIDL)

            # If a card is found
            if status == MIFAREReader.MI_OK:
                print("Card detected")
            
            # Get the UID of the card
            (status,uid) = MIFAREReader.MFRC522_Anticoll()

            # If we have the UID, continue
            if status == MIFAREReader.MI_OK:

                # Print UID
                print("Card read UID: %s,%s,%s,%s" % (uid[0], uid[1], uid[2], uid[3]))
            
                # This is the default key for authentication
                key = [0xFF,0xFF,0xFF,0xFF,0xFF,0xFF]
                
                # Select the scanned tag
                MIFAREReader.MFRC522_SelectTag(uid)

                # Authenticate
                status = MIFAREReader.MFRC522_Auth(MIFAREReader.PICC_AUTHENT1A, blockAddr, key, uid)

                # Check if authenticated
                if status == MIFAREReader.MI_OK:
                    datas = MIFAREReader.MFRC522_Read(blockAddr)
                    MIFAREReader.MFRC522_StopCrypto1()
                else:
                    print("Authentication error")
                    datas = "Authentication Error"

                continue_reading = False
            t3 = t2-t1
            t3 = t3.total_seconds()
            if(t3 > 10):
                return (False,"timeout")
        return datas
    
    def readUUID(self):
        continue_reading = True
        uid = ""
        while continue_reading:
            t2 = datetime.datetime.now()
            # Scan for cards    
            (status,TagType) = MIFAREReader.MFRC522_Request(MIFAREReader.PICC_REQIDL)

            # If a card is found
            if status == MIFAREReader.MI_OK:
                print("Card detected")
            
            # Get the UID of the card
            (status,uid) = MIFAREReader.MFRC522_Anticoll()

            # If we have the UID, continue
            if status == MIFAREReader.MI_OK:

                # Print UID
                print("Card read UID: %s,%s,%s,%s" % (uid[0], uid[1], uid[2], uid[3]))
                uid = "%s,%s,%s,%s" % (uid[0], uid[1], uid[2], uid[3])
                continue_reading = False
                
        
        if(uid == ""):
            return False
        else:
            return uid
    
    def uid_to_num(self, uid):
        print("raw uid",uid)
        n = 0
        for i in range(0, 4):
            n = n * 256 + uid[i]
        return n
    
    def deciphereData(self,listData):
        datas = ""
        for i in listData:
           
            if(i != 0):
                hex_data = hex(i)
                if "0x" in hex_data:
                    hex_data = hex_data.replace("0x","")
                bytes_obj = bytes.fromhex(hex_data)
                ascii_str = bytes_obj.decode("ASCII")
                datas += ascii_str
        
        print("nik",datas)
        
        return datas
    
    def readDataRFID(self):
        ls = ['nama','username','nik','divisi','access']
        dictdata = {}
        for i in ls:
            read = readRFID().readSector(i)
            if(type(read) == tuple):
                return ("failed",read[1])
            data = readRFID().deciphereData(read[1])
            dictdata[i] = data
       
        return dictdata


    

    
# ls = ['nama','username','nik','divisi','access']
# for i in ls:
#     read = readRFID().readSector(i)
#     data = readRFID().deciphereData(read[1])
#     print(data)
# GPIO.cleanup()
