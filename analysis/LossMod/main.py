__author__ = 'Shashank Kapadia'
__copyright__ = '2015 AIR Worldwide, Inc.. All rights reserved'
__version__ = '1.0'
__interpreter__ = 'Python 2.7.10'
__maintainer__ = 'Shashank kapadia'
__email__ = 'skapadia@air-worldwide.com'
__status__ = 'Production'

# ToDo-Shashank: Add option for Location and Contract Summary

# Import standard Python packages
import sys
import logging

# Import internal packages
from database.main import *
from general.main import *

# Import external Python libraries
import pandas as pd


class LossModValidation:

    def __init__(self, server):

        self.setup = dbConnection(server)
        self.connection = self.setup.connection
        self.cursor = self.setup.cursor

    def _check_rule(self, mod_analysis_sid, perils_analysis_grouped, coverage, lob, occupancy, construction,
                    year_built, stories, contract_id, location_id, factor, mod_result_sid, result_db):

        info_analysis = self.setup._getAnalysisInfo(mod_analysis_sid)

        ############################################################################################################
        """
        In the following section, we test for the valid parameter and save by option.

        For example, if the Loss Mod template contains information regarding LOB, then in order to validate it,
        the analysis needs to be saved by either LOB, Contract, Location or Layer

        """
        ############################################################################################################

        # if the Coverage parameter is not empty, check if 'Coverage' option is checked in a result option. Also,
        # if the Layer + Coverage option is not supported
        if any(coverage) and ((not (info_analysis[0][24])) or (info_analysis[0][7] == 'LYR')):

            logging.error('Invalid Parameter + SaveBy option: Coverage Option unchecked or Saved by Layer')
            logging.info('..........Validation Stopped..........')
            sys.exit()

        # if the the Contract ID parameter is not empty, check if the analysis was saved by Contract, Location or Layer
        if any(contract_id) and not info_analysis[0][7] in ['CON', 'LOC', 'LYR']:

            logging.error('Invalid Parameter + SaveBy option: Please save the analysis with the Contract, '
                  'Location or Layer as a Save by option')
            logging.info('..........Validation Stopped..........')
            sys.exit()

        # if the Location ID, yearBuilt, Stories, Construction or Occupancy parameter is not empty, check if analysis
        # was saved by Location
        if (any(location_id) or any(year_built) or any(stories) or any(construction) or any(occupancy)) and not \
                        info_analysis[0][7] in ['LOC']:

            logging.error('Invalid Parameter + SaveBy option: Please save the analysis with the '
                          'Location as a Save by option')
            logging.info('..........Validation Stopped..........')
            sys.exit()

        # if the LOB parameter is not empty, check if the analysis was saved by LOB, Contract, Location or Layer
        if any(lob) and not info_analysis[0][7] in ['EA', 'CON', 'LOC', 'LYR']:

            logging.error('Invalid Parameter + SaveBy option: Please save the analysis with the LOB, '
                          'Contract, Location, or Layer')
            logging.info('..........Validation Stopped..........')
            sys.exit()
        ############################################################################################################
        """
        In the following section, we formulate the lists of necessary information, called template_info, based on the
        save by option. The formulated template info is then used to validate the loss numbers

        For example: if analysis was saved by the LOB, then the template info will contain Perils, LOB, Factor.

        """
        ############################################################################################################

        """
        Option 1:   EA

        Output:     template_info = (Perils, LOB, Factor)

        1. Check if LOB parameter in the template, if not empty, extract the ExposureAttributeSID for a given LOB, else,
        consider all the ExposureAttributeSID

        2. If coverage, add the coverage info to template_info, template_info = (Perils, LOB, Factor, Coverage)

        """

        if info_analysis[0][7] == 'EA':
            lob_update = []
            if any(lob):
                for i in range(len(lob)):
                    self.cursor.execute('Select ExposureAttributeSID from [' + result_db + '].dbo.t' +
                                        str(mod_result_sid) +
                                        '_LOSS_DimExposureAttribute WHERE ExposureAttribute ' + str(lob[i]))
                    info = copy.deepcopy(self.cursor.fetchall())
                    lob_update.append([info[i][0] for i in range(len(info))])
            else:
                for i in range(len(factor)):
                    self.cursor.execute('Select ExposureAttributeSID from [' + result_db + '].dbo.t' +
                                        str(mod_result_sid) + '_LOSS_DimExposureAttribute')
                    info = copy.deepcopy(self.cursor.fetchall())
                    lob_update.append([info[i][0] for i in range(len(info))])
            if any(coverage):
                template_info = zip(perils_analysis_grouped, lob_update, factor, coverage)
            else:
                template_info = zip(perils_analysis_grouped, lob_update, factor)

        """
        Option 2:   Contract or Location

        Output:     if Contract: template_info = (Factor, ContractID, Factor),
                    else Location: template_info = (Factor, ContractID, Factor)

        1. If both LOB and ContractID is present in template, use Loss_DimContract to extract ContractSID from given
        LOB and ContractID

        2. If only LOB or only ContractID is present, use them individually with the same table to extract info

        3. If none is present, extract all the ContractSID; this will account for the case when a template has only
        Peril anf Factor information and analysis was saved by Contract or by Location

        4. If the analysis was run by Contract, update the template info, else, if the analysis was run by Location,
        continue to step 5

        5. If the no information related to LocationID, yearBuilt, Occupancy and stories, then extract the LocationSID
        using the ContractSIDs determined from the above steps and update the template_info, else,

        6.
            1. If LocationID is present, filter the those locations and update the LocationID list
            2. Repeat this process of elimination for Construction, Occupancy, yearBuilt ans stories.

        7. return the updated template_info

        """

        if info_analysis[0][7] in ['CON', 'LOC']:
            contract_id_update = []
            if any(lob) and any(contract_id): # 1.
                for i in range(len(lob)):
                    try:
                        self.cursor.execute('Select ContractSID from [' + result_db + '].dbo.t' +
                                            str(mod_result_sid) + '_LOSS_DimContract WHERE UserLineOfBusiness ' +
                                            str(lob[i]) + 'AND ContractID in ' + str(tuple(contract_id[i].split(','))))
                    except:
                        self.cursor.execute('Select ContractSID from [' + result_db + '].dbo.t' +
                                            str(mod_result_sid) + '_LOSS_DimContract WHERE UserLineOfBusiness ' +
                                            str(lob[i]) + 'AND ContractID = ' + "'" +
                                            str(contract_id[i]) + "'")

                    info = copy.deepcopy(self.cursor.fetchall())
                    contract_id_update.append([info[i][0] for i in range(len(info))])

            elif any(lob): # 2.
                for i in range(len(lob)):
                    self.cursor.execute('Select ContractSID from [' + result_db + '].dbo.t' +
                                        str(mod_result_sid) + '_LOSS_DimContract WHERE UserLineOfBusiness ' +
                                        str(lob[i]))
                    info = copy.deepcopy(self.cursor.fetchall())
                    contract_id_update.append([info[i][0] for i in range(len(info))])

            elif any(contract_id): # 2.
                for i in range(len(contract_id)):
                    try:
                        self.cursor.execute('Select ContractSID from [' + result_db + '].dbo.t' +
                                            str(mod_result_sid) + '_LOSS_DimContract WHERE ContractID in ' + str(
                            tuple(contract_id[i].split(','))))
                    except:
                        self.cursor.execute('Select ContractSID from [' + result_db + '].dbo.t' +
                                            str(mod_result_sid) + '_LOSS_DimContract WHERE ContractID  = ' + "'" +
                                            str(contract_id[i]) + "'")

                    info = copy.deepcopy(self.cursor.fetchall())
                    contract_id_update.append([info[i][0] for i in range(len(info))])
            else: # 3.
                for i in range(len(perils_analysis_grouped)):
                    self.cursor.execute('Select ContractSID from [' + result_db + '].dbo.t' +
                                        str(mod_result_sid) + '_LOSS_DimContract')
                    info = copy.deepcopy(self.cursor.fetchall())
                    contract_id_update.append([info[i][0] for i in range(len(info))])

            if info_analysis[0][7] == 'CON': # 4.
                if any(coverage):
                    template_info = zip(perils_analysis_grouped, contract_id_update, factor, coverage)
                else:
                    template_info = zip(perils_analysis_grouped, contract_id_update, factor)
            else: # 4., 5.
                location_id_update = []
                if not (any(year_built) and any(stories) and any(construction) and (occupancy) and any(location_id)):
                    for i in range(len(contract_id_update)):
                        try:
                            self.cursor.execute(
                                'Select LocationSID from [' + result_db + '].dbo.t' + str(mod_result_sid) +
                                '_LOSS_DimLocation WHERE ContractSID in ' + str(tuple(contract_id_update[i])))
                        except:
                            self.cursor.execute(
                                'Select LocationSID from [' + result_db + '].dbo.t' + str(mod_result_sid) +
                                '_LOSS_DimLocation WHERE ContractSID = ' + "'" +
                                str(contract_id_update[i][0]) + "'")
                        info = copy.deepcopy(self.cursor.fetchall())
                        location_id_update.append([info[i][0] for i in range(len(info))])
                        if any(coverage):
                            template_info = zip(perils_analysis_grouped, location_id_update, factor, coverage)
                        else:
                            template_info = zip(perils_analysis_grouped, location_id_update, factor)
                else: # 6.
                    script = ('Select * from [' + result_db + '].dbo.t' + str(mod_result_sid) +
                                  '_LOSS_DimLocation')
                    dimLocation_DF = pd.read_sql(script, self.connection)
                    location_id_update = []
                    for i in range(len(perils_analysis_grouped)):
                        if any(location_id):
                            try:
                                self.cursor.execute(
                                    'Select LocationSID from [' + result_db + '].dbo.t' + str(mod_result_sid) +
                                    '_LOSS_DimLocation WHERE LocationID in ' + str(
                                        tuple(location_id[i].split(','))))
                            except:
                                self.cursor.execute(
                                    'Select LocationSID from [' + result_db + '].dbo.t' + str(mod_result_sid) +
                                    '_LOSS_DimLocation WHERE LocationID = ' + "'" +
                                    str(location_id[i].split(',')[0]) + "'")
                            info = copy.deepcopy(self.cursor.fetchall())
                            location_sid = [info[j][0] for j in range(len(info))]
                            dimLocation_DF = copy.deepcopy(
                                            dimLocation_DF.loc[dimLocation_DF['LocationSID'].isin(location_sid), :])
                        if any(construction):
                            try:
                                if not construction[i] == None:
                                    dimLocation_DF = copy.deepcopy(
                                        dimLocation_DF.loc[dimLocation_DF['AIRConstructionCode'] == construction[i],
                                        :])
                            except:
                                dimLocation_DF = copy.deepcopy(dimLocation_DF)
                        if any(occupancy):
                            if not occupancy[i] == None:
                                dimLocation_DF = copy.deepcopy(
                                    dimLocation_DF.loc[dimLocation_DF['AIROccupancyCode'] == occupancy[i], :])
                        if any(year_built):
                            if not year_built[i] == None:
                                dimLocation_DF = dimLocation_DF.loc[dimLocation_DF['YearBuilt'] == year_built[i], :]
                        if any(stories):
                            if not stories[i] == None:
                                dimLocation_DF = dimLocation_DF.loc[dimLocation_DF['Stories'] == stories[i], :]

                        location_id_update.append(dimLocation_DF['LocationSID'].values)
                        script = ('Select * from [' + result_db + '].dbo.t' + str(mod_result_sid) +
                                  '_LOSS_DimLocation')
                        dimLocation_DF = pd.read_sql(script, self.connection)
                    if any(coverage): # 7.
                        template_info = zip(perils_analysis_grouped, location_id_update, factor, coverage)
                    else:
                        template_info = zip(perils_analysis_grouped, location_id_update, factor)


        if (info_analysis[0][7] == 'PORT') and (info_analysis[0][8] in ['LOCSUM', 'CONSUM']):

            logging.error('Invalid save by Option: Currently, it doesn''t support the SaveBy Location Summary and'
                          ' Contract Summary option')
            logging.info('..........Validation Stopped..........')
            sys.exit()
        #     # The reason being, each contract may have multiple perils and it is difficult to track the factor
        #     if not len(perils_analysis_grouped) == 1:
        #         print('Currently, Peril+Factor template with save by Location Summary/Contract '
        #               'Summary is only available when analysis is run by single peril')
        #         sys.exit()
        #     else:
        #         if any(contract_id):
        #             contract_id_update = []
        #             for i in range(len(contract_id)):
        #                 self.cursor.execute('Select ContractSID from [' + result_db + '].dbo.t' + str(mod_result_sid) +
        #                                     '_LOSS_DimContract where ContractID in ' + str(
        #                     tuple(contract_id[i].split(','))))
        #                 info = copy.deepcopy(self.cursor.fetchall())
        #                 contract_id_update.append([info[i][0] for i in range(len(info))])
        #         else:
        #             self.cursor.execute('Select ContractSID from [' + result_db + '].dbo.t' + str(mod_result_sid) +
        #                                 '_LOSS_DimContract')
        #             info = copy.deepcopy(self.cursor.fetchall())
        #             contract_id_update = [info[i][0] for i in range(len(info))]
        #         if info_analysis[0][8] == 'CONSUM':
        #             if any(coverage):
        #                 template_info = zip(perils_analysis_grouped, contract_id_update, factor, coverage)
        #             else:
        #                 template_info = zip(perils_analysis_grouped, contract_id_update, factor)
        #         else:
        #             if not (any(year_built) or any(stories) or (construction) or (occupancy)):
        #                 if any(location_id):
        #                     location_id_update = []
        #                     for i in range(len(contract_id_update)):
        #                         try:
        #                             self.cursor.execute(
        #                                 'Select LocationSID from [' + result_db + '].dbo.t' + str(mod_result_sid) +
        #                                 '_LOSS_DimLocation WHERE ContractSID in ' + str(tuple(contract_id_update[i])))
        #                         except:
        #                             self.cursor.execute(
        #                                 'Select LocationSID from [' + result_db + '].dbo.t' + str(mod_result_sid) +
        #                                 '_LOSS_DimLocation WHERE ContractSID = ' + "'" +
        #                                 str(contract_id_update[i][0]) + "'")
        #                         info = copy.deepcopy(self.cursor.fetchall())
        #                         location_id_update.append([info[i][0] for i in range(len(info))])
        #             else:
        #                 query = ('Select * from [' + result_db + '].dbo.t' + str(mod_result_sid) +
        #                          '_LOSS_DimLocation')
        #                 dimLocation_DF = pd.read_sql(query, self.connection)
        #                 location_id_update = []
        #                 for i in range(len(perils_analysis_grouped)):
        #                     if any(construction):
        #                         try:
        #                             if not construction[i] == None:
        #                                 dimLocation_DF = dimLocation_DF.loc[
        #                                                  dimLocation_DF['AIRConstructionCode'] == construction[i], :]
        #                         except:
        #                             dimLocation_DF = dimLocation_DF
        #                     if any(occupancy):
        #                         if not occupancy[i] == None:
        #                             dimLocation_DF = dimLocation_DF.loc[
        #                                              dimLocation_DF['AIROccupancyCode'] == occupancy[i], :]
        #                     if any(year_built):
        #                         if not year_built[i] == None:
        #                             dimLocation_DF = dimLocation_DF.loc[dimLocation_DF['YearBuilt'] == year_built[i], :]
        #                     if any(stories):
        #                         if not stories[i] == None:
        #                             dimLocation_DF = dimLocation_DF.loc[dimLocation_DF['Stories'] == stories[i], :]
        #
        #                     dimLocation_DF_copy = copy.deepcopy(dimLocation_DF)
        #                     location_id_update.append(dimLocation_DF['LocationSID'].values)
        #                 if any(coverage):
        #                     template_info = zip(perils_analysis_grouped, location_id_update, factor)
        #                 else:
        #                     template_info = zip(perils_analysis_grouped, location_id_update, factor, coverage)
        # if (info_analysis[0][7] == 'PORT'):
        #     if any(coverage):
        #         template_info = zip(perils_analysis_grouped, factor, coverage)
        #     else:
        #         template_info = zip(perils_analysis_grouped, factor)
        return template_info

    def _getLossDF(self, ModAnalysisSID, resultDB, BaseResultSID, ModResultSID, coverage):

        info_analysis = self.setup._getAnalysisInfo(ModAnalysisSID)
        resultDF = pd.DataFrame()
        resultDF['Status'] = 1
        # In the case where analysis is saved by LOB, get the loss numbers from Loss By Exposure Attribute
        if info_analysis[0][7] == 'EA':
            resultDF_Base = self.setup._getLossDF(resultDB, BaseResultSID, 'LOB')
            resultDF_Mod = self.setup._getLossDF(resultDB, ModResultSID, 'LOB')

        # In the case where analysis is saved by Default, get the loss numbers from Loss By Event
        if info_analysis[0][7] == 'PORT':

            if info_analysis[0][8] == 'CONSUM':

                resultDF_Base = self.setup._getLossDF(resultDB, BaseResultSID, 'CONSUM')
                resultDF_Mod = self.setup._getLossDF(resultDB, ModResultSID, 'CONSUM')

            elif info_analysis[0][8] == 'LOCSUM':

                resultDF_Base = self.setup._getLossDF(resultDB, BaseResultSID, 'LOCSUM')
                resultDF_Mod = self.setup._getLossDF(resultDB, ModResultSID, 'LOCSUM')

            else:

                resultDF_Base = self.setup._getLossDF(resultDB, BaseResultSID, 'Event')
                resultDF_Mod = self.setup._getLossDF(resultDB, ModResultSID, 'Event')

        # In the case where analysis is saved by Contract, get the loss numbers from Loss By Contract
        if info_analysis[0][7] == 'CON':

            resultDF_Base = self.setup._getLossDF(resultDB, BaseResultSID, 'CON')
            resultDF_Mod = self.setup._getLossDF(resultDB, ModResultSID, 'CON')

        # In the case where analysis is saved by Location, get the loss numbers from Loss By Location
        elif info_analysis[0][7] == 'LOC':

            resultDF_Base = self.setup._getLossDF(resultDB, BaseResultSID, 'LOC')
            resultDF_Mod = self.setup._getLossDF(resultDB, ModResultSID, 'LOC')

        # In the case where analysis is saved by Layer, get the loss numbers from Loss By Layer
        elif info_analysis[0][7] == 'LYR':

            resultDF_Base = self.setup._getLossDF(resultDB, BaseResultSID, 'LYR')
            resultDF_Mod = self.setup._getLossDF(resultDB, ModResultSID, 'LYR')

        # PerilSet Code as key only if the analysis wasn't run by LocSummary or ConSummary
        if not info_analysis[0][8] in ['LOCSUM', 'CONSUM']:
            resultDF['PerilSetCode'] = resultDF_Mod['PerilSetCode']

        if info_analysis[0][7] == 'EA':
            resultDF['ExposureAttributeSID'] = resultDF_Mod['ExposureAttributeSID']

        if info_analysis[0][7] == 'CON':
            resultDF['ContractSID'] = resultDF_Mod['ContractSID']

        if info_analysis[0][7] == 'LOC':
            resultDF['LocationSID'] = resultDF_Mod['LocationSID']

        if info_analysis[0][7] == 'LYR':
            resultDF['LayerSID'] = resultDF_Mod['LayerSID']

        if info_analysis[0][7] == 'GEOL':
            resultDF['GeographySID'] = resultDF_Mod['GeographySID']

        if info_analysis[0][7] == 'CONGEOL':
            resultDF['ContractSID'] = resultDF_Mod['ContractSID']
            resultDF['GeographySID'] = resultDF_Mod['GeographySID']

        if info_analysis[0][8] == 'LOCSUM':
            resultDF['LocationSID'] = resultDF_Mod['LocationSID']

        if info_analysis[0][8] == 'CONSUM':
            resultDF['ContractSID'] = resultDF_Mod['ContractSID']

        resultDF['GroundUpLoss_Base'] = resultDF_Base.loc[:, 'GroundUpLoss']
        resultDF['GroundUpLoss_Mod'] = resultDF_Mod.loc[:, 'GroundUpLoss']
        resultDF['Ratio'] = resultDF_Mod.loc[:, 'GroundUpLoss'] / resultDF_Base.loc[:, 'GroundUpLoss']

        if any(coverage):

            coverages = ['A', 'B', 'C', 'D']
            for i in coverages:
                resultDF['GroundUpLoss' + i + '_Base'] = resultDF_Base.loc[:, 'GroundUpLoss_' + i]
                resultDF['GroundUpLoss' + i + '_Mod'] = resultDF_Mod.loc[:, 'GroundUpLoss_' + i]
                resultDF['GroundUpLoss' + i + '_Ratio'] = resultDF_Mod.loc[:, 'GroundUpLoss_' + i] / resultDF_Base.loc[
                                                                                                     :,
                                                                                                     'GroundUpLoss_' + i]
        else:
            coverages = ['A', 'B', 'C', 'D']
            for i in coverages:
                resultDF['GroundUpLoss' + i + '_Base'] = '-'
                resultDF['GroundUpLoss' + i + '_Mod'] = '-'
                resultDF['GroundUpLoss' + i + '_Ratio'] = '-'
        resultDF.loc[:, 'Status'] = 1

        return resultDF

    def _validate(self, resultDF, template_info, coverage, ModAnalysisSID):

        info_analysis = self.setup._getAnalysisInfo(ModAnalysisSID)

        ############################################################################################################
        '''

        Validation Rule: In this module we validate the application of loss mod template.

        Pseudo Algorithm:
            1. For each template info:
                if the analysis is not saved by Location Summary or Contract Summary
                    if the Coverage is not present
                        if the analysis wasn't saved ByDefault:

                            PART 1:
                                - For the given Key template info rows, the ratio should be equal to given Factor
                                (Example: for selected ContractID 1, 2, 3, 4: Ratio should be 4)
                                - Calculate the difference between given ratio and calculated ratio
                                - if the absolute difference is less than 0.001, Pass, else, Fail

                            PART 2:
                                - For all other rows, for which the status column won't be updated, given Factor is assumed
                                to be 1
                                - Calculate the difference between given ratio and calculated ratio (also should be 1)
                                - if the absolute difference is less than 0.001, Pass, else, Fail
                        else if the analysis was saved byDefault:

                            Everything is SAME but, in this case Key is different

                    else if Coverage is present

                        if the analysis wasn't saved ByDefault:
                            Everything is SAME, but in this scenario, we also calcuate the ratio and difference for
                            Coverage loss

                        else if the analysis was saved byDefault:
                            Same as Above

        '''
        ############################################################################################################

        for i in range(len(template_info)):

            if not info_analysis[0][8] in ['LOCSUM', 'CONSUM']:

                if not any(coverage):
                    if info_analysis[0][7] != 'PORT':

                        resultDF.loc[(resultDF['PerilSetCode'].isin(template_info[i][0])) &
                                     (resultDF.iloc[:, 2].isin(template_info[i][1])), 'Input_Ratio'] = float(
                            template_info[i][2])
                        resultDF.loc[(resultDF['PerilSetCode'].isin(template_info[i][0])) &
                                     (resultDF.iloc[:, 2].isin(template_info[i][1])), 'Difference'] = \
                            resultDF.loc[(resultDF['PerilSetCode'].isin(template_info[i][0])) & (
                                resultDF.iloc[:, 2].isin(template_info[i][1])), 'Ratio'] - float(template_info[i][2])

                        if (abs(resultDF[(resultDF['PerilSetCode'].isin(template_info[i][0])) &
                            (resultDF.iloc[:, 2].isin(template_info[i][1]))]['Difference']) < 0.001).all():
                            resultDF.loc[(resultDF['PerilSetCode'].isin(template_info[i][0])) &
                                         (resultDF.iloc[:, 2].isin(template_info[i][1])), 'Status'] = 'Pass'
                        else:
                            resultDF.loc[(resultDF['PerilSetCode'].isin(template_info[i][0])) &
                                         (resultDF.iloc[:, 2].isin(template_info[i][1])), 'Status'] = 'Fail'

                        if ((resultDF[resultDF['Status'] == 1.0]['Ratio'] - 1.0).all() < 0.001).all():
                            resultDF.loc[resultDF['Status'] == 1.0, 'Input_Ratio'] = 1.0
                            resultDF.loc[resultDF['Status'] == 1.0, 'Difference'] = resultDF.loc[resultDF[
                                                                                                     'Status'] == 1.0, 'Ratio'] - 1.0
                            resultDF.loc[resultDF['Status'] == 1.0, 'Status'] = 'Pass'

                    else:

                        resultDF.loc[(resultDF['PerilSetCode'].isin(template_info[i][0])), 'Input_Ratio'] = float(
                            template_info[i][1])
                        resultDF.loc[(resultDF['PerilSetCode'].isin(template_info[i][0])), 'Difference'] = \
                            resultDF.loc[(resultDF['PerilSetCode'].isin(template_info[i][0])), 'Ratio'] - float(
                                template_info[i][1])

                        if (abs(resultDF[(resultDF['PerilSetCode'].isin(template_info[i][0]))][
                                    'Difference']) < 0.001).all():
                            resultDF.loc[(resultDF['PerilSetCode'].isin(template_info[i][0])), 'Status'] = 'Pass'
                        else:
                            resultDF.loc[(resultDF['PerilSetCode'].isin(template_info[i][0])), 'Status'] = 'Fail'

                        if ((resultDF[resultDF['Status'] == 1.0]['Ratio'] - 1.0).all() < 0.001).all():
                            resultDF.loc[resultDF['Status'] == 1.0, 'Input_Ratio'] = 1.0
                            resultDF.loc[resultDF['Status'] == 1.0, 'Difference'] = resultDF.loc[resultDF[
                                                                                                     'Status'] == 1.0, 'Ratio'] - 1.0
                            resultDF.loc[abs(resultDF['Difference']) < 0.001, 'Status'] = 'Pass'
                            resultDF.loc[abs(resultDF['Difference']) > 0.001, 'Status'] = 'Fail'
                else:
                    if info_analysis[0][7] != 'PORT':
                        coverages = list(template_info[i][3])
                        for j in coverages:

                            resultDF.loc[(resultDF['GroundUpLoss' + j + '_Mod'] == 0) & (
                                resultDF['PerilSetCode'].isin(template_info[i][0])) &
                                         (resultDF.iloc[:, 2].isin(
                                             template_info[i][1])), 'GroundUpLoss' + j + '_Ratio'] = float(
                                template_info[i][2])

                            resultDF.loc[(resultDF['PerilSetCode'].isin(template_info[i][0])) &
                                         (resultDF.iloc[:, 2].isin(template_info[i][1])) & (
                                             resultDF['GroundUpLoss' + j + '_Ratio'] != 1), 'Input_Ratio_' + j] = float(
                                template_info[i][2])
                            resultDF.loc[(resultDF['PerilSetCode'].isin(template_info[i][0])) &
                                         (resultDF.iloc[:, 2].isin(template_info[i][1])) & (
                                             resultDF['GroundUpLoss' + j + '_Ratio'] != 1), 'Difference_' + j] = \
                                resultDF.loc[(resultDF['PerilSetCode'].isin(template_info[i][0])) & (
                                    resultDF.iloc[:, 2].isin(template_info[i][1])) & (resultDF[
                                                                                          'GroundUpLoss' + j + '_Ratio'] != 1), 'GroundUpLoss' + j + '_Ratio'] - float(
                                    template_info[i][2])

                            if (abs(resultDF[(resultDF['PerilSetCode'].isin(template_info[i][0])) &
                                (resultDF.iloc[:, 2].isin(template_info[i][1])) & (
                                        resultDF['GroundUpLoss' + j + '_Ratio'] != 1)]['Difference_' + j].fillna(
                                0)) < 0.001).all():
                                resultDF.loc[(resultDF['PerilSetCode'].isin(template_info[i][0])) &
                                             (resultDF.iloc[:, 2].isin(template_info[i][1])) & (
                                                 resultDF['GroundUpLoss' + j + '_Ratio'] != 1), 'Status'] = 'Pass'

                            resultDF = resultDF.fillna(1)

                            resultDF.loc[:, 'Difference_' + j] = resultDF.loc[:, 'GroundUpLoss' + j + '_Ratio'] - resultDF.loc[:,
                                                                                                  'Input_Ratio_' + j]
                            resultDF.loc[abs(resultDF['Difference_' + j]) < 0.001, 'Status'] = 'Pass'

                            resultDF.loc[abs(resultDF['Difference_' + j]) > 0.001, 'Status'] = 'Fail'

                    else:
                        coverages = list(template_info[i][2])
                        for j in coverages:
                            resultDF.loc[
                                resultDF['GroundUpLoss' + j + '_Mod'] == 0, 'GroundUpLoss' + j + '_Ratio'] = float(
                                template_info[i][1])
                            resultDF.loc[
                                (resultDF['PerilSetCode'].isin(template_info[i][0])), 'Input_Ratio_' + j] = float(
                                template_info[i][1])

                            resultDF.loc[(resultDF['PerilSetCode'].isin(template_info[i][0])), 'Difference_' + j] = \
                                resultDF.loc[(resultDF['PerilSetCode'].isin(
                                    template_info[i][0])), 'GroundUpLoss' + j + '_Ratio'] - float(template_info[i][1])

                            if (abs(resultDF[(resultDF['PerilSetCode'].isin(template_info[i][0]))][
                                            'Difference_' + j]) < 0.001).all():
                                resultDF.loc[(resultDF['PerilSetCode'].isin(template_info[i][0])), 'Status'] = 'Pass'

                            resultDF = resultDF.fillna(1)
                            resultDF.loc[:, 'Difference_' + j] = resultDF.loc[:,
                                                                 'GroundUpLoss' + j + '_Ratio'] - resultDF.loc[:,
                                                                                                  'Input_Ratio_' + j]
                            resultDF.loc[abs(resultDF['Difference_' + j]) < 0.001, 'Status'] = 'Pass'
                            resultDF.loc[abs(resultDF['Difference_' + j]) > 0.001, 'Status'] = 'Fail'

            elif info_analysis[0][8] == 'LOCSUM':

                resultDF.loc[(resultDF['LocationSID'].isin(template_info[i][0])), 'Input_Ratio'] = float(
                    template_info[i][1])
                resultDF.loc[(resultDF['LocationSID'].isin(template_info[i][0])), 'Difference'] = \
                    resultDF.loc[(resultDF['LocationSID'].isin(template_info[i][0])), 'Ratio'] - float(
                        template_info[i][1])

                if (abs(resultDF[(resultDF['LocationSID'].isin(template_info[i][0]))]['Difference']) < 0.001).all():
                    resultDF.loc[(resultDF['LocationSID'].isin(template_info[i][0])), 'Status'] = 'Pass'
                else:
                    resultDF.loc[(resultDF['LocationSID'].isin(template_info[i][0])), 'Status'] = 'Fail'

                if ((resultDF[resultDF['Status'] == 1.0]['Ratio'] - 1.0 < 0.001).all()):
                    resultDF.loc[resultDF['Status'] == 1.0, 'Input_Ratio'] = 1.0
                    resultDF.loc[resultDF['Status'] == 1.0, 'Difference'] = \
                        resultDF.loc[resultDF['Status'] == 1.0, 'Ratio'] - 1.0
                    resultDF.loc[resultDF['Status'] == 1.0, 'Status'] = 'Pass'

            elif info_analysis[0][8] == 'CONSUM':

                resultDF.loc[(resultDF['ContractSID'].isin(template_info[i][0])), 'Input_Ratio'] = float(
                    template_info[i][1])
                resultDF.loc[(resultDF['ContractSID'].isin(template_info[i][0])), 'Difference'] = \
                    resultDF.loc[(resultDF['ContractSID'].isin(template_info[i][0])), 'Ratio'] - float(
                        template_info[i][1])

                if (abs(resultDF[(resultDF['ContractSID'].isin(template_info[i][0]))]['Difference']) < 0.001).all():
                    resultDF.loc[(resultDF['ContractSID'].isin(template_info[i][0])), 'Status'] = 'Pass'
                else:
                    resultDF.loc[(resultDF['ContractSID'].isin(template_info[i][0])), 'Status'] = 'Fail'

                if (resultDF[resultDF['Status'] == 1.0]['Ratio'] - 1.0 < 0.001).all():
                    resultDF.loc[resultDF['Status'] == 1.0, 'Input_Ratio'] = 1.0
                    resultDF.loc[resultDF['Status'] == 1.0, 'Difference'] = \
                        resultDF.loc[resultDF['Status'] == 1.0, 'Ratio'] - 1.0
                    resultDF.loc[resultDF['Status'] == 1.0, 'Status'] = 'Pass'

        resultDF.loc[resultDF['Status'] == 1.0, 'Status'] = 'Fail'
        if info_analysis[0][7] == 'PORT':
            resultDF.rename(columns={str(resultDF.columns.values[1]): 'ID'}, inplace=True)

        else:
            resultDF.insert(1, "ID",
                            [str(resultDF.iloc[:, 1].values[i]) + '_' + str(resultDF.iloc[:, 2].values[i]) for i in
                             range(len(resultDF.iloc[:, 1]))])
            resultDF.drop(resultDF.columns[[2, 3]], axis=1, inplace=True)

        if not 'Input_Ratio' in resultDF.columns:
            resultDF['Input_Ratio'] = '-'
            resultDF['Difference'] = '-'

        for i in ['A', 'B', 'C', 'D']:
            if not 'Difference_' + i in resultDF.columns:
                resultDF['Difference_' + i] = '-'
                resultDF['Input_Ratio_' + i] = '-'

        resultDF = set_column_sequence(resultDF, ['Status', 'ID', 'GroundUpLoss_Mod', 'GroundUpLoss_Base',
                                                  'Ratio', 'Input_Ratio', 'Difference',
                                                  'GroundUpLossA_Mod', 'GroundUpLossA_Base',
                                                  'GroundUpLossA_Ratio', 'Input_Ratio_A',
                                                  'Difference_A', 'GroundUpLossB_Mod',
                                                  'GroundUpLossB_Base', 'GroundUpLossB_Ratio', 'Input_Ratio_B',
                                                  'Difference_B', 'GroundUpLossC_Mod',
                                                  'GroundUpLossC_Base', 'GroundUpLossC_Ratio', 'Input_Ratio_C',
                                                  'Difference_C', 'GroundUpLossD_Mod',
                                                  'GroundUpLossD_Base', 'GroundUpLossD_Ratio', 'Input_Ratio_D',
                                                  'Difference_D'])

        return resultDF