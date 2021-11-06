import json
import pymysql


class mysqlController:
    def __init__(self,connectionJson):
        self.connectionJson = connectionJson
    
    def test(self):
        return "hahaha"
    
    def openfile(self,filenamejson):
        with open(filenamejson) as json_file:
            data = json.load(json_file)
            return data
    
    def connection(self):
        connection = pymysql.connect(host=self.connectionJson['hostname'],
                             user=self.connectionJson['username'],
                             password=self.connectionJson['password'],
                             database = self.connectionJson['dbname'],
                             charset='utf8mb4')
        
        return connection
    
    def checkVersion(self):
        con = self.connection()
        print(con)
        returnVal = ""
        try:
            with con.cursor() as cur:
                cur.execute('SELECT VERSION()')
                version = cur.fetchone()
                returnVal = f'Database version: {version[0]}'
        finally:
            con.close()
        
        return returnVal

    def selectQuery(self,query):
        con = self.connection()
        returnVal = ""
        err = ""
        try:
            with con.cursor() as cur:
                cur.execute(query)
                version = cur.fetchall()
                returnVal = version
        except Exception as e:
            err = e
        finally:
            con.close()
        
        if(err == ""):
            return returnVal
        else:
            return str(err)
    
    def CUDQuery(self,query):
        con = self.connection()
        err = ""
        print("start query")
        try:
            with con.cursor() as cur:
                cur.execute(query)
                con.commit()
        except Exception as e:
            err = e
        finally:
            con.close()
        print("end query")
        if(err == ""):
            return True
        else:
            return str(err)
    
    def closeCon(self):
        self.connection().close()
    
    def CUDQueryAlone(self,con,query):
        err = ""
        try:
            with con.cursor() as cur:
                cur.execute(query)
                con.commit()
        except Exception as e:
            err = e
        if(err == ""):
            return True
        else:
            return str(err)
    
    def selectQueryAlone(self,con,query):
        returnVal = ""
        err = ""
        try:
            with con.cursor() as cur:
                cur.execute(query)
                version = cur.fetchall()
                returnVal = version
        except Exception as e:
            err = e
        
        if(err == ""):
            return returnVal
        else:
            return str(err)

        
        
