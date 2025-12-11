import xml.etree.ElementTree as ET


class HadronsXML:
    @staticmethod
    def setValue(branch, name, value):
        e = ET.SubElement(branch, name)
        e.text = str(value)

    @staticmethod
    def setValues(branch, names_values):
        for name, value in names_values:
            e = ET.SubElement(branch, name)
            e.text = str(value)
        
    def __init__(self):
        self.root = ET.Element("grid")
        self.tree = ET.ElementTree(self.root)
        self.parameters = ET.SubElement(self.root, "parameters")
        self.modules = ET.SubElement(self.root, "modules")
        
        self.trajcounter = ET.SubElement(self.parameters, "trajCounter")

        ####
        self.database = ET.SubElement(self.parameters, "database")
        self.setValue(self.database, "applicationDb", "app.db")
        self.setValue(self.database, "resultDb", "results.db")
        self.setValue(self.database, "restoreModules", "false")
        self.setValue(self.database, "restoreMemoryProfile", "false")
        self.setValue(self.database, "restoreSchedule", "false")
        #self.setValue(self.database, "makeStatDb","false")
        self.setValue(self.database, "statDbBase", "stats.db")
        self.setValue(self.database, "statDbPeriodMs", 1000)
        self.setValue(self.database, "statDbAllRanks", "false")

        self.genetic = ET.SubElement(self.parameters, "genetic")
        self.setValue(self.genetic, "popSize", 20)
        self.setValue(self.genetic, "maxGen", 100)
        self.setValue(self.genetic, "maxCstGen", 100)
        self.setValue(self.genetic, "mutationRate", 0.1)

        self.setValue(self.parameters, "graphFile", "")
        self.setValue(self.parameters, "scheduleFile", "")
        self.setValue(self.parameters, "saveSchedule", "false")
        self.setValue(self.parameters, "parallelWriteMaxRetry", -1)
        
        
    def setTrajCounter(self, start,end,step):
        self.setValue(self.trajcounter, "start", start)
        self.setValue(self.trajcounter, "end", end)
        self.setValue(self.trajcounter, "step", step)
        

    def addModule(self, name, type):
        m = ET.SubElement(self.modules, "module")
        mid = ET.SubElement(m, "id")
        self.setValue(mid, "name", name)
        self.setValue(mid, "type", type)
        opt = ET.SubElement(m, "options")
        return opt
        
    def setRunID(self, id_):
        self.setValue(self.parameters, "runId", id_)
        
    def write(self,filename):
        ET.indent(self.tree, space="  ")
        self.tree.write(filename, xml_declaration=True)


       
#xml = HadronsXML()
#m = xml.addModule("gauge", "MIO::LoadNersc")
#xml.setValue(m, "file", "/path/to/config")#

#xml.setTrajCounter(0,1,1)
#xml.write("test.xml")


    #   <parameters>
    # <!-- trajectory loop, the trajectory number is appended as a suffix -->
    # <!-- to file read an written by modules. It is also part of the     -->
    # <!-- RNG seed.                                                      -->
    # <trajCounter>
    #   <start>1500</start>
    #   <end>1520</end>
    #   <step>20</step>
    # </trajCounter>
#ET.indent(tree, space="  ")
#tree.write("test.xml", xml_declaration=True)
