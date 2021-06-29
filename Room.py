'''
Created on Jul 12, 2020

@author: willg
'''
import Race
import Placement
import Player
import WiimfiSiteFunctions
import UserDataProcessing

from _collections import defaultdict
import UtilityFunctions
from TagAI import getTagSmart
from common import log_text, ERROR_LOGGING_TYPE

class Room(object):
    '''
    classdocs
    '''
    def __init__(self, rLIDs, roomSoup, races=None, roomID=None, set_up_user=None, display_name=""):
        self.name_changes = {}
        self.removed_races = []
        
        self.initialize(rLIDs, roomSoup, races, roomID)
        self.playerPenalties = defaultdict(int)
        
        #for each race, holds fc_player dced that race, and also holds 'on' or 'before'
        self.dc_on_or_before = defaultdict(dict)
        self.set_up_user = set_up_user
        self.set_up_user_display_name = display_name
        self.forcedRoomSize = {}
        self.miis = {}
        
        

    
    def initialize(self, rLIDs, roomSoup, races=None, roomID=None):
        self.rLIDs = rLIDs
        
        if roomSoup == None:
            raise Exception
        if self.rLIDs == None or len(self.rLIDs) == 0:
            #TODO: Here? Caller should?
            roomSoup.decompose()
            raise Exception
        
        races_old = None
        if 'races' in self.__dict__:
            races_old = self.races
            
            
        self.races = races
        self.roomID = roomID
        if self.races == None:
            self.races = self.getRacesList(roomSoup, races_old)
        if len(self.races) > 0:
            self.roomID = self.races[0].roomID
        else:
            self.rLIDs = None
            self.races = None
            self.roomID = None
            raise Exception
        
        
    
    
    def is_initialized(self):
        return self.races != None and self.rLIDs != None and len(self.rLIDs) > 0
        
    
    def had_positions_changed(self):
        if self.races != None:
            for race in self.races:
                if race.placements_changed:
                    return True
        return False
    

    #Outside caller should use this, it will add the removed race to the class' history
    def remove_race(self, raceIndex):
        if raceIndex >= 0 and raceIndex < len(self.races):
            raceName = self.races[raceIndex].getTrackNameWithoutAuthor()
            remove_success = self.__remove_race__(raceIndex)
            if remove_success:
                self.removed_races.append((raceIndex, raceName))
            return remove_success, (raceIndex, raceName)
        return False, None
    
    def __remove_race__(self, raceIndex, races=None):
        if races==None:
            races=self.races
        if raceIndex >= 0 and raceIndex < len(races):
            del races[raceIndex]
            return True
        return False
    
    def get_removed_races_string(self):
        removed_str = ""
        for raceInd, raceName in self.removed_races:
            removed_str += "- " + raceName + " (originally race #" + str(raceInd+1) + ") removed by tabler\n"
        return removed_str
    
    
    def getFCPlayerList(self, startrace=1,endrace=12):
        fcNameDict = {}
        if endrace is None:
            endrace = len(self.races)
        for race in self.races[startrace-1:endrace]:
            for placement in race.getPlacements():
                FC, name = placement.get_fc_and_name()
                fcNameDict[FC] = name
        return fcNameDict
    
    def getFCPlayerListString(self, startrace=1,endrace=12, lounge_replace=True):
        FCPL = self.getFCPlayerList(startrace, endrace)
        to_build = ""
        for fc, name in FCPL.items():
            to_build += fc + ": " + UtilityFunctions.process_name(name + UserDataProcessing.lounge_add(fc, lounge_replace)) + "\n"
        return to_build
    
    def getPlayerPenalities(self):
        return self.playerPenalties
        
    def addPlayerPenalty(self, fc, amount):
        self.playerPenalties[fc] += amount
        
    
    def getFCPlayerListStartEnd(self, startRace, endRace):
        fcNameDict = {}
        for raceNumber, race in enumerate(self.races, 1):
            if raceNumber >= startRace and raceNumber <= endRace: 
                for placement in race.getPlacements():
                    FC, name = placement.get_fc_and_name()
                    fcNameDict[FC] = name
        return fcNameDict
    
    def getNameChanges(self):
        return self.name_changes
    
    def setNameForFC(self, FC, name):
        self.name_changes[FC] = name
    
    def getFCs(self):
        return self.getFCPlayerList(endrace=None).keys()
    
    def getPlayers(self):
        return self.getFCPlayerList(endrace=None).values()
    
            
    def setRaces(self, races):
        self.races = races
        
    def getRaces(self):
        return self.races
    
    def getRXXText(self):
        resultText = ""
        if len(self.rLIDs) == 1:
            rxx = self.rLIDs[0]
            resultText = f"**Room URL:** https://wiimmfi.de/stats/mkwx/list/{rxx}  |  **rxx number:** {rxx}\n"
        else:
            resultText = "**?mergeroom** was used, so there are multiple rooms:\n\n"
            for i, rxx in enumerate(self.rLIDs[::-1], 1):
                resultText += f"**- Room #{i} URL:** https://wiimmfi.de/stats/mkwx/list/{rxx}  |  **rxx number:** {rxx}\n"
        return resultText
            
    
    def getMissingPlayersPerRace(self):
        numGPS = int(len(self.races)/4 + 1)
        GPPlayers = []
        missingPlayers = []
        for GPNum in range(numGPS):
            GPPlayers.append(self.getFCPlayerListStartEnd((GPNum*4)+1, (GPNum+1)*4))
        
        for raceNum, race in enumerate(self.races):
            thisGPPlayers = GPPlayers[int(raceNum/4)]
            missingPlayersThisRace = []
            if raceNum % 4 != 0: #not the start of the GP:
                for fc, player in thisGPPlayers.items():
                    if fc not in race.getFCs():
                        missingPlayersThisRace.append((fc, player))
            missingPlayers.append(missingPlayersThisRace)
        return missingPlayers
    
    def getMissingOnRace(self, numGPS):
        GPPlayers = []
        missingPlayers = []
        for GPNum in range(numGPS):
            GPPlayers.append(self.getFCPlayerListStartEnd((GPNum*4)+1, (GPNum+1)*4))
        
        wentMissingThisGP = []
        for raceNum, race in enumerate(self.races[0:numGPS*4]):
            if raceNum/4 >= len(GPPlayers): #To avoid any issues if they put less GPs than the room has
                break
            thisGPPlayers = GPPlayers[int(raceNum/4)]
            missingPlayersThisRace = []
            if raceNum % 4 == 0:
                wentMissingThisGP = []
            
            if raceNum % 4 != 0: #not the start of the GP:
                for fc, player in thisGPPlayers.items():
                    if fc not in race.getFCs() and fc not in wentMissingThisGP:
                        wentMissingThisGP.append(fc)
                        missingPlayersThisRace.append((fc, player))
            missingPlayers.append(missingPlayersThisRace)
        for missingPlayersOnRace in missingPlayers:
            missingPlayersOnRace.sort()
        return missingPlayers
    
    
    def getDCListString(self, numberOfGPs=3, replace_lounge=True):
        missingPlayersByRace = self.getMissingOnRace(numberOfGPs)
        missingPlayersAmount = sum([len(x) for x in missingPlayersByRace])
        if missingPlayersAmount == 0:
            last_race = self.races[-1]
            return False, "No one has DCed. Last race: " + str(last_race.track) + " (Race #" + str(last_race.raceNumber) + ")"
        else:
            counter = 1
            build_string = "*Disconnection List:*\n"
            for raceNum, missing_players in enumerate(missingPlayersByRace, 1):
                for fc, player in sorted(missing_players):
                    build_string += "\t" + str(counter) + ". **"
                    build_string += UtilityFunctions.process_name(player + UserDataProcessing.lounge_add(fc, replace_lounge)) + "** disconnected on or before race #" + str(raceNum) + " (" + str(self.races[raceNum-1].getTrackNameWithoutAuthor()) + ")\n"
                    counter+=1
            return True, build_string
    
    #method that returns the players in a consistent, sorted order - first by getTagSmart, then by FC (for tie breaker)
    #What is returned is a list of tuples (fc, player_name)
    def get_sorted_player_list(self, startrace=1, endrace=12):
        players = list(self.getFCPlayerListStartEnd(startrace, endrace).items())
        return sorted(players, key=lambda x: (getTagSmart(x[1]), x[0]))
       
       
    def get_sorted_player_list_string(self, startrace=1, endrace=12, lounge_replace=True):
        players = self.get_sorted_player_list(startrace, endrace)
        to_build = ""
        for list_num, (fc, player) in enumerate(players, 1):
            to_build += str(list_num) + ". " + UtilityFunctions.process_name(player + UserDataProcessing.lounge_add(fc, lounge_replace)) + "\n"
        return to_build
            
            
    def get_players_list_string(self, startrace=1, endrace=12, lounge_replace=True):
        player_list = self.get_sorted_player_list(startrace, endrace)
        build_str = ""
        for counter, (fc, player) in enumerate(player_list, 1):
            build_str += str(counter) + ". " + UtilityFunctions.process_name(player)
            if lounge_replace:
                build_str += UtilityFunctions.process_name(UserDataProcessing.lounge_add(fc, lounge_replace))
            build_str += "\n"
        return build_str
    
    #SOUP LEVEL FUNCTIONS
    
    @staticmethod
    def getPlacementInfo(line):
        allRows = line.find_all("td")
    
        FC = str(allRows[0].find("span").string)
    
        roomPosition = -1
        role = "-1"

        if (allRows[1].find("b") != None):
            roomPosition = 1
            role = "host"
        else:
            temp = str(allRows[1].string).strip().split()
            roomPosition = temp[0].strip(".")
            role = temp[1]
        
        #TODO: Handle VR?
        vr = str(-1)
        
        time = str(allRows[8].string)
        
        playerName = str(allRows[9].string)
        
        while len(allRows) > 0:
            del allRows[0]
        
        return FC, roomPosition, role, vr, time, playerName
    
    def getRaceInfoFromList(self, textList):
        '''Utility Function'''
        raceTime = str(textList[0])
        UTCIndex = raceTime.index("UTC")
        raceTime = raceTime[:UTCIndex+3]
        
        matchID = str(textList[1])
        
        raceNumber = str(textList[2]).strip().strip("(").strip(")").strip("#")
        
        roomID = str(textList[4])
        
        roomType = str(textList[6])
        
        cc = str(textList[7])[3:-2] #strip white spaces, the star, and the cc
        
        track = "Unknown_Track (Bad HTML, mkwx messed up)"
        if 'rLIDs' in self.__dict__:
            track += str(self.rLIDs)
        try:
            track = str(textList[9])
        except IndexError:
            pass
        
        placements = []
        
        while len(textList) > 0:
            del textList[0]
        
        return raceTime, matchID, raceNumber, roomID, roomType, cc, track, placements
      
    def getRacesList(self, roomSoup, races_old=None):
        #Utility function
        tableLines = roomSoup.find_all("tr")
        
        foundRaceHeader = False
        races = []
        for line in tableLines:
            if foundRaceHeader:
                foundRaceHeader = False
            else:
                if (line.get('id') != None): #Found Race Header
                    #_ used to be the racenumber, but mkwx deletes races 24 hours after being played. This leads to rooms getting races removed, and even though
                    #they have race numbers, the number doesn't match where they actually are on the page
                    #This was leading to out of bounds exceptions.
                    raceTime, matchID, _, roomID, roomType, cc, track, placements = self.getRaceInfoFromList(line.findAll(text=True))
                    raceNumber = None
                    races.insert(0, Race.Race(raceTime, matchID, raceNumber, roomID, roomType, cc, track))
                    foundRaceHeader = True
                else:
                    FC, roomPosition, role, vr, time, playerName = self.getPlacementInfo(line)
                    if races[0].hasFC(FC):
                        FC = FC + "-2"
                    plyr = Player.Player(FC, playerName, role, roomPosition, vr)
                    
                    if plyr.FC in self.name_changes:
                        plyr.name = self.name_changes[plyr.FC] + " (Tabler Changed)"
                    p = Placement.Placement(plyr, -1, time)
                    races[0].addPlacement(p)
        
        #We have a memory leak, and it's not incredibly clear how BS4 objects work and if
        #Python's automatic garbage collection can figure out how to collect
        while len(tableLines) > 0:
            del tableLines[0]
        
        for raceNum, race in enumerate(races, 1):
            race.raceNumber = raceNum
        
        if races_old != None:
            for race in races_old:
                if race.placements_changed:
                    races[race.raceNumber-1].placements_changed = True
                    for (index, newIndex) in race.placement_history:
                        races[race.raceNumber-1].insertPlacement(index, newIndex)
                        
        for removed_race_ind, _ in self.removed_races:
            self.__remove_race__(removed_race_ind, races)
            
        for raceNum, race in enumerate(races, 1):
            race.raceNumber = raceNum
        
        return races
    

    #Soup level functions
    
    def getNumberOfGPS(self):
        return int((len(self.races)-1)/4)+1
    
    async def update_room(self):
        if self.is_initialized():
            soups = []
            rLIDs = []
            for rLID in self.rLIDs:
                
                _, rLID_temp, tempSoup = await WiimfiSiteFunctions.getRoomData(rLID)
                soups.append(tempSoup)
                rLIDs.append(rLID_temp)
                
            tempSoup = WiimfiSiteFunctions.combineSoups(soups)
            
            to_return = False
            if tempSoup != None:
                self.initialize(rLIDs, tempSoup)
                tempSoup.decompose()
                del tempSoup
                to_return = True
                    
            while len(soups) > 0:
                soups[0].decompose()
                del soups[0]
            return to_return
        return False
        
    def getRacesPlayed(self):
        return [r.track for r in self.races]
    
    def get_races_abbreviated(self, last_x_races=None):
        if last_x_races == None:
            temp = []
            for ind,race in enumerate(self.races, 1):
                if race.getAbbreviatedName() == None:
                    return None
                temp.append(str(ind) + ". " + race.getAbbreviatedName())
            return " | ".join(temp)
        else:
            temp = []
            for ind,race in enumerate(self.races[-last_x_races:], 1):
                if race.getAbbreviatedName() == None:
                    return None
                temp.append(str(ind) + ". " + race.getAbbreviatedName())
            return " | ".join(temp)
        
    
    def get_races_string(self, races=None):
        if races == None:
            races = self.getRacesPlayed()
        string_build = ""
        num = 1
        for race in races:
            string_build += "Race #" + str(num) + ": " + race + "\n"
            num += 1
        if len(string_build) < 1:
            string_build = "No races played yet."
        return UtilityFunctions.process_name(string_build)
    
    def get_loungenames_in_room(self):
        all_fcs = self.getFCs()
        lounge_names = []
        for FC in all_fcs:
            lounge_name = UserDataProcessing.lounge_get(FC)
            if lounge_name != "":
                lounge_names.append(lounge_name)
        return lounge_names
    
    def get_loungenames_can_modify_table(self):
        can_modify = self.get_loungenames_in_room()
        if self.set_up_user_display_name is not None and self.set_up_user_display_name != "":
            can_modify.append(str(self.set_up_user_display_name))
        elif self.set_up_user is not None:
            can_modify.append(str(self.set_up_user))
        return can_modify
            
    
    def canModifyTable(self, discord_id:int):
        if self.getSetupUser() == None or self.getSetupUser() == discord_id:
            return True
        discord_ids = [data[0] for data in self.getRoomFCDiscordIDs().values()]
        return str(discord_id) in discord_ids
        
    def getRoomFCDiscordIDs(self):
        FC_DID = {FC:(None, None) for FC in self.getFCs()}
        for FC in FC_DID:
            if FC in UserDataProcessing.FC_DiscordID:
                FC_DID[FC] = UserDataProcessing.FC_DiscordID[FC]
        return FC_DID
        
    
    def getSetupUser(self):
        return self.set_up_user
    
    def setSetupUser(self, setupUser, displayName:str):
        self.set_up_user = setupUser
        self.set_up_user_display_name = displayName
    

    def forceRoomSize(self, raceNum, roomSize):
        self.forcedRoomSize[raceNum] = roomSize
    
    def getRoomSize(self, raceNum):
        if raceNum in self.forcedRoomSize:
            return self.forcedRoomSize[raceNum]
       
    #This is not the entire save state of the class, but rather, the save state for edits made by the user 
    def get_recoverable_save_state(self):
        save_state = {}
        save_state['name_changes'] = self.name_changes.copy()
        save_state['removed_races'] = self.removed_races.copy()
        save_state['playerPenalties'] = self.playerPenalties.copy()
        
        #for each race, holds fc_player dced that race, and also holds 'on' or 'before'
        save_state['dc_on_or_before'] = self.dc_on_or_before.copy()
        save_state['forcedRoomSize'] = self.forcedRoomSize.copy()
        save_state['rLIDs'] = self.rLIDs.copy()
        save_state['races'] = {}
        for race in self.races:
            matchID = race.matchID
            recoverable_save_state = race.get_recoverable_state()
            try:
                save_state['races'][matchID] = recoverable_save_state
            except Exception as e:
                log_text(f"Error in Room.get_recoverable_save_state() putting race in dictionary: {str(matchID)}", ERROR_LOGGING_TYPE)
                log_text(str(e), ERROR_LOGGING_TYPE)
        
        return save_state
    
    def restore_save_state(self, save_state):
        for save_attr, save_value in save_state.items():
            if save_attr != 'races':
                self.__dict__[save_attr] = save_value
        races_save_state = save_state['races']
        for race in self.races:
            if race.matchID in races_save_state:
                race.restore_save_state(races_save_state[race.matchID])
                
        
        
        
    
        