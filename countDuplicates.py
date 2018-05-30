# encoding: utf-8

import gvsig

from gvsig import commonsdialog
from org.gvsig.andami import Utilities
import os, time
from org.gvsig.app.project.documents.table import TableManager
from gvsig.libs.toolbox import ToolboxProcess
from org.gvsig.tools import ToolsLocator
from gvsig.uselib import use_plugin

use_plugin('org.gvsig.h2spatial.app.mainplugin')

from org.h2.mvstore import MVStore #, OffHeapStore

def main(*args):
    process = CountDuplicates()
    process.selfregister("Scripting")
    #gm = GeoProcessLocator.getGeoProcessManager()
    # Actualizamos el interface de usuario de la Toolbox
    process.updateToolbox()

def createDiskDataBase():
    dbFile = gvsig.getTempFile("db",".maps")
    store = MVStore.Builder().fileName(dbFile).open()
    d = store.openMap("db1")
    return store, d
      
class CountDuplicates(ToolboxProcess):    
    def defineCharacteristics(self):
      i18nManager = ToolsLocator.getI18nManager()
      self.setName(i18nManager.getTranslation("_Count_features_with_duplicates_field"))
      self.setGroup(i18nManager.getTranslation("_Analysis"))
      self.setDescription(i18nManager.getTranslation("_Create_a_table_counting_duplicates_in_the_features_by_a_field"))
          
      params = self.getParameters()
      params.addInputTable("inputTable", i18nManager.getTranslation("_Table"), True)
      params.addTableField("tableField", i18nManager.getTranslation("_Field"), "inputTable", True)
    def processAlgorithm(self):
      i18nManager = ToolsLocator.getI18nManager()
      params = self.getParameters()
      table = params.getParameterValueAsTable("inputTable")#gvsig.currentTable()
      field = params.getParameterValueAsInt("tableField")#str(commonsdialog.inputbox("Name of the field"))
      limitNumberOfKeys = 10
      store = None
      try:
          #import pdb
          #pdb.set_trace()
          features = table.getBaseDataObject().getFeatureStore().getFeatureSet()
      except:
          commonsdialog.msgbox("Table not opened")
          return False
          
      count = dict()
      size = features.getSize()
      self.setRangeOfValues(0, size)
      #self.getStatus().setTitle("Processing..")
      self.setProgressText(i18nManager.getTranslation("_Counting_features"))
      n = 0
      numberOfKeys = 0
      changedToDB = False
      
      for f in features:
        n += 1
        ff = str(f.get(field))
        if ff in count.keys():
          count[ff] += 1
        else:
          count[ff] = 1
          numberOfKeys += 1

        # Check if is necessary change to a disk db for keys
        if changedToDB is False and numberOfKeys > limitNumberOfKeys:
          changedToDB = True
          store, temp = createDiskDataBase()
          for k in count.keys():
              temp[k] = count[k]
          count = temp
          store.commit()
          
        # Save db each 50000 values
        if n % 50000 == 0 and changedToDB is True:
          store.commit()
        
        # Each 100000 values make a commit if db is being used
        if self.isCanceled() is True:
          return False
        else:
          self.next()
          
      if changedToDB is True and store != None:
          store.commit()
          
      sch = gvsig.createFeatureType()
      sch.append('ID','STRING',15)
      sch.append('COUNT','INTEGER',20)

      dbf = gvsig.createDBF(sch, gvsig.getTempFile("count",".dbf"))
      
      dbf.edit()
      for k,v in count.iteritems():
        f = dbf.createNewFeature()
        f.set('ID',k)
        f.set('COUNT',v)
        dbf.insert(f)
   
      dbf.commit()

      if changedToDB is True and store != None:
        store.close()

      d = gvsig.loadDBF( dbf.getFullName())
      d.setName(i18nManager.getTranslation("_Count_Duplicates_Table"))
      return True