"""
Author: Stefan Coe, Dianna Martinez & Andy Norton, 2012
This module has a class to answer Spatial Questions Associated with MTP Project
Prioritization and insert/update answers to Web Form Database. All GIS data used
in this module is located here:
W:\gis\projects\DianaM\python_class\psrc\data\mtp_prioritization_data\mtp_priorit_data.gdb
Only use data from this source!!!
"""

# Import system modules
import arcpy
from arcpy import env
import sqlite3
import logging
import pyodbc
import tempfile
import os
from ..genfun.generalfunctions import fileobjectexists

class mtpProjectPrioritization:
    """Class to Answer Spatial Questions Associated with MTP Project Prioritization. Provides access to memebers that
        answer questions and insert/update answers to Web Form Database"""
  
    

    def __init__(self, gdb_workspace):
        """
        Initialize Class. Pass in a Geodatabase workspace location.
        """
        
        fileobjectexists(gdb_workspace)
        self.gdb_workspace = gdb_workspace
        env.workspace = self.gdb_workspace
        env.overwriteOutput = True
        self.tempDirectory = tempfile.mkdtemp()
        self.conn = sqlite3.connect(self.tempDirectory + "/mydatabase")
        self.c = self.conn.cursor()
       
        
    def updateDatabase(self, responseList, sqlconnection):
        """
        Function to update web form database. responseList should be in the following format:
        [projectID, QuestionNumber, Answer String)
        """
        questionID = responseList[1]
        cnxn = pyodbc.connect(sqlconnection)
        cursor = cnxn.cursor()
        
        cursor.execute("Select ID from Projects where MTPID = ?", responseList[0])
        
        row = cursor.fetchone()
        #Get the local id (database id) for this particular mtp project
        localID = row[0]
        x = str(responseList[2])
        #Get the AnswerID that corresponds to our answer
        cursor.execute("Select ID from Answers where QuestionID = ? and Value = ?", responseList[1], x)
        row = cursor.fetchone()
        answerID = row[0]
       
        #Need to check if there is a reponse for this question yet!
        cursor.execute("Select * from Responses where ProjectID = ? and QuestionID = ?", localID, questionID)
       #print cursor.fetchall()
        y = cursor.fetchall()
        
        if len(y) == 0:
                cursor.execute("Insert Into Responses (AnswerID, ProjectID, QuestionID) Values (?, ?, ?)",  answerID, localID, questionID)
                cnxn.commit()
                cnxn.close()
                print "added" 
        else:
                        
                cursor.execute("Update Responses set AnswerID = ? where ProjectID = ? and QuestionID = ?", answerID, localID, responseList[1])
                cnxn.commit()
                cnxn.close()
        return "database updated"
                
        
    def Question16_17(self, listOfUniqueProjects):
        """
        logic to answer question 16 & 17, returns a list of unique projectIDs
        """
        responseList = []
        
        for projID in listOfUniqueProjects:
            self.c.execute("select sum(Length) as sumLen, projID, County_COD from projects where\
                    projID=:ID group by projID, County_COD order by projID, sumLen desc", {"ID": projID})
            x = 0
            #get info from the first and (and if it exists in two counties) second rows
            for a in self.c:
                if x == 0:
                    firstCounty = a[2]
                    firstLength = a[0]
                    x = x + 1
                elif x == 1:
                    secondCounty = a[2]
                    secondLength = a[0]
                    x = x + 1
                else:
                    x = x + 1
                    row2 = rows2.next()
                    
            #Project is only in one county
            if x == 1:
                y = (projID, 16, firstCounty)
                responseList.append(y)
                y = (projID, 17, -1)
                responseList.append(y)
            #project is in two counties:
            else:
                y = (projID, 16, firstCounty)
                responseList.append(y)
                y = (projID, 17, secondCounty)
                responseList.append(y)
                
                
        return responseList


    def geoprocBoundaryQuestions(self, fc_Projects):
        """
        Performs Geoprocessing for boundary questions. Creates a table in the sqlite database
        to perform queries against. 
        """
        
        #Intersect Project with Geographies (in this case counties)
        inFeatures = [fc_Projects, "Counties"]
        intersectOutput = "outIntersect"
        arcpy.Intersect_analysis(inFeatures, intersectOutput, "", 0.01, "line")
        
        self.c.execute('drop table if exists projects')
        #Create a table with the needed fields from the intersect output
        self.c.execute('''create table projects
        (projID text, projRteID long, Length double, County_COD text)''')
        #Need to make a table view from intersect output
        arcpy.MakeTableView_management(intersectOutput, "projects_tview")
        rows = arcpy.SearchCursor("projects_tview")
        row = rows.next()
        #get a list of projects
        projectList = []
        #loop through the table view and add data to sqlite table
        while row:
        #make sure RteID is integer, which means its an MTP project, not a TIP project
            if isinstance( row.projRteID, ( int, long ) ):
                myprojID = row.projID
                myprojRteID = row.projRteID
                myLength = row.Shape_Length
                myCountyCode = row.County_COD
                projectList.append(myprojID)
                self.c.execute("insert into projects (projID, projRteID, Length, County_COD) values (?, ?, ?, ?)",
                    (myprojID, myprojRteID, myLength, myCountyCode))
                row = rows.next()
            else:
                row = rows.next()
        #Get a set of unique projects    
        uniqueProjects = set(projectList)
        return uniqueProjects



        # Save (commit) the changes
        self.conn.commit()
        #projInfoList = []

def runPrioritization(projects, geodatabase, sqlconnection):
    
    classMTP = mtpProjectPrioritization("W:/gis/projects/stefan/PythonProject/test.gdb")
    myUniqueProjects = classMTP.geoprocBoundaryQuestions(projects)

    myResponses = classMTP.Question16_17(myUniqueProjects)
    print myResponses
    for item in myResponses:
        b = classMTP.updateDatabase(item, sqlconnection)
        print b



#os.removedirs(tempDirectory)
#loop through unique project



#for item in projInfoList:
    #updateQuery(item) 

