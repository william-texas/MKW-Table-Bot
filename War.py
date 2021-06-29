'''
Created on Jul 13, 2020

@author: willg
'''

import ErrorChecker
from _collections import defaultdict
import random
import TableBotExceptions

tableColorPairs = [("#244f96", "#cce7e8"),
                   ("#D11425","#E8EE28"),
                   ("#E40CA6","#ADCFCD"),
                   ("#2EFF04","#FF0404"),
                   ("#193FFF","#FF0404"),
                   ("#ff8cfd","#fdff8c"),
                   ("#96c9ff","#ffbe96"),
                   ("#ffbbb1","#b1ffd9"),
                   ("#ff69b4","#b4ff69"),
                   ("#95eefa","#58cede"),
                   ("#54ffc9","#54e3ff"),
                   ("#a1ff3d","#fcff3d"),
                   ("#8d8ce6","#cfceff")]







class War(object):
    '''
    classdocs
    '''

    __formatMapping = {u"ffa":1,u"1v1":1, u"2v2":2, u"3v3":3, u"4v4":4, u"5v5":5, u"6v6":6}

    def __init__(self, formatt, numberOfTeams, numberOfGPs=3, missingRacePts=3, ignoreLargeTimes=False, displayMiis=True):
        self.teamColors = None
        self.setWarFormat(formatt, numberOfTeams)
        self.numberOfGPs = numberOfGPs
        self.warName = None
        self.missingRacePts = missingRacePts
        self.manualEdits = {}
        self.ignoreLargeTimes = ignoreLargeTimes
        self.displayMiis = displayMiis
        self.teamPenalties = defaultdict(int)
        self.forcedRoomSize = {}
        self.teams = None
        
        
    def setWarFormat(self, formatting, numberOfTeams):
        if formatting not in self.__formatMapping:
            raise TableBotExceptions.InvalidWarFormatException()
        
        try: 
            int(numberOfTeams)
        except ValueError:
            raise TableBotExceptions.InvalidNumberOfPlayersException()
        
        if self.__formatMapping[formatting.lower().strip()] * int(numberOfTeams) > 12:
            raise TableBotExceptions.InvalidNumberOfPlayersException()
        
        self.formatting = formatting.lower()
        self.numberOfTeams = int(numberOfTeams)
        self.playersPerTeam = self.__formatMapping[self.formatting]
        if self.numberOfTeams == 2:
            self.teamColors = random.choice(tableColorPairs)
        
    def setTeams(self, teams):
        #teams is a dictionary of FCs, each FC having a tag
        self.teams = teams
        
    def getTeamForFC(self, FC):
        if self.teams is None:
            raise TableBotExceptions.WarSetupStillRunning()
        if FC in self.teams:
            return self.teams[FC]
        return "NO TEAM"
    
    def setTeamForFC(self, FC, team):
        if self.teams is None:
            raise TableBotExceptions.WarSetupStillRunning()
        self.teams[FC] = team
    
    def getTags(self):
        if self.teams is None:
            raise TableBotExceptions.WarSetupStillRunning()
        return set(self.teams.values())
    
    def getFCsForTag(self, tagToGet):
        if self.teams is None:
            raise TableBotExceptions.WarSetupStillRunning()
        return [fc for fc, tag in self.teams.items() if tag == tagToGet]
        
        
    def print_teams(self):
        if self.teams is None:
            raise TableBotExceptions.WarSetupStillRunning()
        for tag in self.getTags(self, self.teams):
            print(tag + self.getFCsForTag(tag))
            
    def addEdit(self, FC, gpNum, gpScore):
        if FC not in self.manualEdits:
            self.manualEdits[FC] = []
        
        index = None
        #Need to remove previous edit for this player's GP, if it exists
        for i, (this_gpNum, _) in enumerate(self.manualEdits[FC]):
            if this_gpNum == gpNum:
                index = i
                break
        if index != None:
            del self.manualEdits[FC][index]
            
        self.manualEdits[FC].append((gpNum, gpScore))
    
    def getEditsForGP(self, gpNum):
        gp_edits = []
        for FC, edits in self.manualEdits.items():
            for curGPNum, score in edits:
                if curGPNum == gpNum:
                    gp_edits.append((FC, score))
        return gp_edits
    
    def getEditAmount(self, FC, gpNum):
        if FC in self.manualEdits:
            for edit in self.manualEdits[FC]:
                if edit[0] == gpNum:
                    return edit[1]
        return None
                    
    def getTeamPenalities(self):
        return self.teamPenalties
        
    def addTeamPenalty(self, team_tag, amount):
        self.teamPenalties[team_tag] += amount   
    
    def __str__(self):
        war_string = "-- WAR --"
        war_string += "\nNumber of teams: " + str(self.numberOfTeams)
        war_string += "\nFormat: " + str(self.formatting)
        war_string += "\nNumber of players: " + str(self.numberOfTeams*self.playersPerTeam)
        return war_string
    
    def is_ffa(self):
        return self.formatting == "1v1" or self.formatting == "ffa"
    
    
    def get_num_players(self):
        return self.numberOfTeams*self.playersPerTeam
            

    def get_war_errors_string_2(self, room, replaceLounge=True):
        errors = ErrorChecker.get_war_errors_players(self, room, replaceLounge, ignoreLargeTimes=self.ignoreLargeTimes)
        if errors == None:
            return "Room not loaded."
        
        errors_no_large_times = ErrorChecker.get_war_errors_players(self, room, replaceLounge, ignoreLargeTimes=True)
        errors_large_times = ErrorChecker.get_war_errors_players(self, room, replaceLounge, ignoreLargeTimes=False)
        num_errors_no_large_times = sum( [ len(raceErrors) for raceErrors in errors_no_large_times.values()])
        num_errors_large_times = sum( [ len(raceErrors) for raceErrors in errors_large_times.values()])
        build_string = "Errors that might affect the table:\n"
        
        removedRaceString = room.get_removed_races_string()
        build_string += removedRaceString
        
        if self.ignoreLargeTimes and num_errors_no_large_times < num_errors_large_times:
            build_string += "- Large times occurred, but are being ignored. Table could be incorrect.\n"
        

        
        elif len(errors) == 0 and len(removedRaceString) == 0:
            return "Room had no errors. Table should be correct."
        
        
            
        for raceNum, error_messages in sorted(errors.items(), key=lambda x:x[0]):
            if raceNum > len(room.races):
                build_string += "   Race #" + str(raceNum) + ":\n"
            else:
                build_string += "   Race #" + str(raceNum) + " (" + room.races[raceNum-1].getTrackNameWithoutAuthor() + "):\n"
            
            for error_message in error_messages:
                build_string += "\t- " + error_message + "\n"
        return build_string
    
    def get_all_war_errors_players(self, room, lounge_replace=True):
        return ErrorChecker.get_war_errors_players(self, room, lounge_replace, ignoreLargeTimes=False)
    

    def setWarName(self, warName):
        self.warName = warName
        
    def getWarName(self, numRaces:int):
        if self.teams is None:
            raise TableBotExceptions.WarSetupStillRunning()
        if self.warName != None:
            return self.warName
        war_string = ""
        if self.is_ffa():
            war_string += "FFA"
            war_string += " (" + str(numRaces) + " races)"
            return war_string
        for teamTag in set(self.teams.values()):
            war_string += teamTag + " vs "
        if len(war_string) > 0:
            war_string = war_string[:-4]
        
        war_string += ": " + self.formatting
        war_string += " (" + str(numRaces) + " races)"
        return war_string
    
    def getTableWarName(self, numRaces:int):
        if self.warName == None:
            return str(numRaces) + " races"
        else:
            return self.getWarName(numRaces)
    
    def getNumberOfGPS(self):
        return self.numberOfGPs
    
    def get_recoverable_save_state(self):
        save_state = {}
        save_state['warName'] = self.warName
        save_state['manualEdits'] = self.manualEdits.copy()
        save_state['teamPenalties'] = self.teamPenalties.copy()
        
        save_state['forcedRoomSize'] = self.forcedRoomSize.copy()
        save_state['teams'] = self.teams.copy()
        return save_state
    
    def restore_save_state(self, save_state):
        for save_attr, save_value in save_state.items():
            self.__dict__[save_attr] = save_value
    
        
            
        