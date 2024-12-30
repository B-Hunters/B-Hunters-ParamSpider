from .__version__ import __version__
import subprocess
import json
import os
from urllib.parse import urlparse
from b_hunters.bhunter import BHunters
from karton.core import Task
import shutil
import re
from bson.objectid import ObjectId

class paramspiderm(BHunters):
    """
    B-Hunters-ParamSpider developed by 0xBormaa
    """

    identity = "B-Hunters-ParamSpider"
    version = __version__
    persistent = True
    filters = [
        
        {
            "type": "subdomain", "stage": "new"
        }
    ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
                    
    def scan(self,url):        
        result=self.katanacommand(url)
        
        return result
    def katanacommand(self,url):
        result=[]

        try:
            outputfile=self.generate_random_filename()
            output = subprocess.run(["paramspider","-o",outputfile,"-d", url ], capture_output=True, text=True, timeout=900)
            data=output.stdout.split("\n")
            try:
                
                # Open the file in read mode
                if os.path.exists(outputfile):
                    with open(outputfile, "r") as file:
                        # Read the contents of the file
                        file_contents = file.read()
                        data=file_contents.split("\n")
                        result=data
                    os.remove(outputfile)
            except Exception as e:
                self.log.error(e)
                                


        except Exception as e:
            print("error ",e)
            # result=[]
        return result
    
    def process(self, task: Task) -> None:
        source=task.payload["source"]
        url = task.payload["data"]
        domain = task.payload["subdomain"]
        db=self.db
        self.scanid=task.payload_persistent["scan_id"]
        
        report_id=task.payload_persistent["report_id"]
        collection = db["domains"]
        self.scanid=task.payload_persistent["scan_id"]
        try:
                
            self.log.info("Starting processing new url")
            self.log.warning(url)
            domain = re.sub(r'^https?://', '', domain)
            domain = domain.rstrip('/')
            self.update_task_status(domain,"Started")
            result=self.scan(url)
            self.waitformongo()
            db=self.db
            collection = db["links"]
            urlstripped = re.sub(r'^https?://', '', url)
            urlstripped = urlstripped.rstrip('/')
            result = list(set(result))
            existing_document = collection.find_one({"report_id":ObjectId(report_id),"source":self.identity})
            new_links=[]
            if existing_document:
                existing_links = existing_document.get("Links", [])
                new_links = [link for link in result if link not in existing_links]
            else:
                new_links=result
            if new_links !=[] and new_links!=[url]:
                resultdata = "\n".join(map(lambda x: str(x), new_links)).encode()
                self.log.info("Uploading data of "+url)
                senddata=self.backend.upload_object("bhunters","paramspider_"+self.scanid+"_"+self.encode_filename(urlstripped),resultdata)
                collection.update_one({"report_id": ObjectId(report_id),"source":self.identity}, {"$push": {f"Links": {"$each": new_links}}}, upsert=True)

                tag_task = Task(
                    {"type": "paths", "stage": "scan"},
                    payload={"data": urlstripped,
                            "subdomain":domain,
                    "source":"paramspider",
                    "type":"file"
                    }
                )
                self.send_task(tag_task)

            # Get domain_id from domain
            collection = db["domains"]
            jsdata=[]
            for i in result:
                
                if ".js" in i and i !="":
                    
                    try:
                        if self.checkjs(i):

                            collection2 = db["js"]
                            existing_document = collection2.find_one({"report_id":ObjectId(report_id),"url": i})
                            if existing_document is None:
                                jsdata.append(i)
                                tag_task = Task(
                                    {"type": "js", "stage": "new"},
                                    payload={"data": url,
                                    "subdomain":domain,
                                    "file": i,
                                    "module":"katana"
                                    }
                                )
                                self.send_task(tag_task)
                    except Exception as e:
                        raise Exception(e)
    
            self.update_task_status(domain,"Finished")

        except Exception as e:
            self.update_task_status(domain,"Failed")
            raise Exception(e)
