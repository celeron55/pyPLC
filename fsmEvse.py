# State machine for the charger
#
#

#------------------------------------------------------------

import pyPlcTcpSocket
import time # for time.sleep()
from helpers import prettyHexMessage, combineValueAndMultiplier
from mytestsuite import * 
from random import random
from exiConnector import * # for EXI data handling/converting

stateWaitForSupportedApplicationProtocolRequest = 0
stateWaitForSessionSetupRequest = 1
stateWaitForServiceDiscoveryRequest = 2
stateWaitForServicePaymentSelectionRequest = 3
stateWaitForFlexibleRequest = 4
stateWaitForChargeParameterDiscoveryRequest = 5
stateWaitForCableCheckRequest = 6
stateWaitForPreChargeRequest = 7
stateWaitForPowerDeliveryRequest = 8

class fsmEvse():
    def addToTrace(self, s):
        self.callbackAddToTrace("[EVSE] " + s)

    def publishStatus(self, s):
        self.callbackShowStatus(s, "evseState")
        
    def enterState(self, n):
        self.addToTrace("from " + str(self.state) + " entering " + str(n))
        if (self.state!=0) and (n==0):
            self.publishStatus("Waiting f AppHandShake")
        self.state = n
        self.cyclesInState = 0
        
    def isTooLong(self):
        # The timeout handling function.
        return (self.cyclesInState > 100) # 100*33ms=3.3s
        
        
    def stateFunctionWaitForSupportedApplicationProtocolRequest(self):
        if (len(self.rxData)>0):
            self.addToTrace("In state WaitForSupportedApplicationProtocolRequest, received " + prettyHexMessage(self.rxData))
            exidata = removeV2GTPHeader(self.rxData)
            self.rxData = []
            strConverterResult = exiDecode(exidata, "DH") # Decode Handshake-request
            self.addToTrace(strConverterResult)
            if (strConverterResult.find("ProtocolNamespace=urn:din")>0):
                # todo: of course we should care for schemaID and prio also here
                self.addToTrace("Detected DIN")
                # Eh for encode handshake, SupportedApplicationProtocolResponse
                msg = addV2GTPHeader(exiEncode("Eh"))
                self.addToTrace("responding " + prettyHexMessage(msg))
                self.Tcp.transmit(msg)
                self.publishStatus("Schema negotiated")
                self.enterState(stateWaitForSessionSetupRequest)
        
    def stateFunctionWaitForSessionSetupRequest(self):
        if (len(self.rxData)>0):
            self.simulatedPresentVoltage = 0
            self.addToTrace("In state WaitForSessionSetupRequest, received " + prettyHexMessage(self.rxData))
            exidata = removeV2GTPHeader(self.rxData)
            self.rxData = []
            strConverterResult = exiDecode(exidata, "DD")
            self.addToTrace(strConverterResult)
            if (strConverterResult.find("SessionSetupReq")>0):
                # todo: check the request content, and fill response parameters
                msg = addV2GTPHeader(exiEncode("EDa")) # EDa for Encode, Din, SessionSetupResponse
                self.addToTrace("responding " + prettyHexMessage(msg))
                self.Tcp.transmit(msg)
                self.publishStatus("Session established")
                self.enterState(stateWaitForServiceDiscoveryRequest)
        if (self.isTooLong()):
            self.enterState(0)
            
    def stateFunctionWaitForServiceDiscoveryRequest(self):
        if (len(self.rxData)>0):
            self.addToTrace("In state WaitForServiceDiscoveryRequest, received " + prettyHexMessage(self.rxData))
            exidata = removeV2GTPHeader(self.rxData)
            self.rxData = []
            strConverterResult = exiDecode(exidata, "DD")
            self.addToTrace(strConverterResult)
            if (strConverterResult.find("ServiceDiscoveryReq")>0):
                # todo: check the request content, and fill response parameters
                msg = addV2GTPHeader(exiEncode("EDb")) # EDb for Encode, Din, ServiceDiscoveryResponse
                self.addToTrace("responding " + prettyHexMessage(msg))
                self.Tcp.transmit(msg)
                self.publishStatus("Services discovered")
                self.enterState(stateWaitForServicePaymentSelectionRequest)
        if (self.isTooLong()):
            self.enterState(0)
            
    def stateFunctionWaitForServicePaymentSelectionRequest(self):
        if (len(self.rxData)>0):
            self.addToTrace("In state WaitForServicePaymentSelectionRequest, received " + prettyHexMessage(self.rxData))
            exidata = removeV2GTPHeader(self.rxData)
            self.rxData = []
            strConverterResult = exiDecode(exidata, "DD")
            self.addToTrace(strConverterResult)
            if (strConverterResult.find("ServicePaymentSelectionReq")>0):
                # todo: check the request content, and fill response parameters
                msg = addV2GTPHeader(exiEncode("EDc")) # EDc for Encode, Din, ServicePaymentSelectionResponse
                self.addToTrace("responding " + prettyHexMessage(msg))
                self.Tcp.transmit(msg)
                self.publishStatus("ServicePayment selected")
                self.enterState(stateWaitForFlexibleRequest) # todo: not clear, what is specified. The Ioniq sends PowerDeliveryReq as next.
        if (self.isTooLong()):
            self.enterState(0)
            
    def stateFunctionWaitForFlexibleRequest(self):
        if (len(self.rxData)>0):
            self.addToTrace("In state WaitForFlexibleRequest, received " + prettyHexMessage(self.rxData))
            exidata = removeV2GTPHeader(self.rxData)
            self.rxData = []
            strConverterResult = exiDecode(exidata, "DD")
            self.addToTrace(strConverterResult)
            if (strConverterResult.find("PowerDeliveryReq")>0):
                # todo: check the request content, and fill response parameters
                msg = addV2GTPHeader(exiEncode("EDh")) # EDh for Encode, Din, PowerDeliveryResponse
                self.addToTrace("responding " + prettyHexMessage(msg))
                self.publishStatus("PowerDelivery")
                self.Tcp.transmit(msg)  
                self.enterState(stateWaitForFlexibleRequest) # todo: not clear, what is specified in DIN
            if (strConverterResult.find("ChargeParameterDiscoveryReq")>0):
                # todo: check the request content, and fill response parameters
                msg = addV2GTPHeader(exiEncode("EDe")) # EDe for Encode, Din, ChargeParameterDiscoveryResponse
                self.addToTrace("responding " + prettyHexMessage(msg))
                self.publishStatus("ChargeParamDiscovery")
                self.Tcp.transmit(msg)  
                self.enterState(stateWaitForFlexibleRequest) # todo: not clear, what is specified in DIN               
            if (strConverterResult.find("CableCheckReq")>0):
                # todo: check the request content, and fill response parameters
                msg = addV2GTPHeader(exiEncode("EDf")) # EDf for Encode, Din, CableCheckResponse
                self.addToTrace("responding " + prettyHexMessage(msg))
                self.publishStatus("CableCheck")
                self.Tcp.transmit(msg)  
                self.enterState(stateWaitForFlexibleRequest) # todo: not clear, what is specified in DIN
            if (strConverterResult.find("PreChargeReq")>0):
                # check the request content, and fill response parameters
                uTarget = 220 # default in case we cannot decode the requested voltage
                try:
                    y = json.loads(strConverterResult)
                    strEVTargetVoltageValue = y["EVTargetVoltage.Value"]
                    strEVTargetVoltageMultiplier = y["EVTargetVoltage.Multiplier"]
                    uTarget = combineValueAndMultiplier(strEVTargetVoltageValue, strEVTargetVoltageMultiplier)
                    self.addToTrace("EV wants EVTargetVoltage " + str(uTarget))
                except:
                    self.addToTrace("ERROR: Could not decode the PreChargeReq")

                # simulating preCharge
                if (self.simulatedPresentVoltage<uTarget/2):
                    self.simulatedPresentVoltage = uTarget/2
                if (self.simulatedPresentVoltage<uTarget-30):
                    self.simulatedPresentVoltage += 20
                if (self.simulatedPresentVoltage<uTarget):
                    self.simulatedPresentVoltage += 5
                strPresentVoltage = str(self.simulatedPresentVoltage) # "345"
                self.callbackShowStatus(strPresentVoltage, "EVSEPresentVoltage")
                msg = addV2GTPHeader(exiEncode("EDg_"+strPresentVoltage)) # EDg for Encode, Din, PreChargeResponse
                if (testsuite_faultinjection_is_triggered(TC_EVSE_Shutdown_during_PreCharge)):
                    # send a PreChargeResponse with StatusCode EVSE_Shutdown, to simulate a user-triggered session stop
                    msg = addV2GTPHeader("809a02180189551e24fc9e9160004100008182800000")
                self.addToTrace("responding " + prettyHexMessage(msg))
                self.publishStatus("PreCharging " + strPresentVoltage)
                self.Tcp.transmit(msg)  
                self.enterState(stateWaitForFlexibleRequest) # todo: not clear, what is specified in DIN     
            if (strConverterResult.find("ContractAuthenticationReq")>0):
                # todo: check the request content, and fill response parameters
                msg = addV2GTPHeader(exiEncode("EDl")) # EDl for Encode, Din, ContractAuthenticationResponse
                self.addToTrace("responding " + prettyHexMessage(msg))
                self.publishStatus("ContractAuthentication")
                self.Tcp.transmit(msg)  
                self.enterState(stateWaitForFlexibleRequest) # todo: not clear, what is specified in DIN     
            if (strConverterResult.find("CurrentDemandReq")>0):
                # check the request content, and fill response parameters
                uTarget = 220 # default in case we cannot decode the requested voltage
                try:
                    y = json.loads(strConverterResult)
                    strEVTargetVoltageValue = y["EVTargetVoltage.Value"]
                    strEVTargetVoltageMultiplier = y["EVTargetVoltage.Multiplier"]
                    uTarget = combineValueAndMultiplier(strEVTargetVoltageValue, strEVTargetVoltageMultiplier)
                    self.addToTrace("EV wants EVTargetVoltage " + str(uTarget))
                    strSoc = y["DC_EVStatus.EVRESSSOC"]
                    self.callbackShowStatus(strSoc, "soc")
                except:
                    self.addToTrace("ERROR: Could not decode the CurrentDemandReq")
                self.simulatedPresentVoltage = uTarget + 3*random() # The charger provides the voltage which is demanded by the car.
                strPresentVoltage = str(self.simulatedPresentVoltage)
                self.callbackShowStatus(strPresentVoltage, "EVSEPresentVoltage")
                strEVSEPresentCurrent = "1" # Just as a dummy current
                msg = addV2GTPHeader(exiEncode("EDi_"+strPresentVoltage + "_" + strEVSEPresentCurrent)) # EDi for Encode, Din, CurrentDemandRes
                if (testsuite_faultinjection_is_triggered(TC_EVSE_Malfunction_during_CurrentDemand)):
                    # send a CurrentDemandResponse with StatusCode EVSE_Malfunction, to simulate e.g. a voltage overshoot
                    msg = addV2GTPHeader("809a02203fa9e71c31bc920100821b430b933b4b7339032b93937b908e08043000081828440201818000040060a11c06030306402038441380")
                self.addToTrace("responding " + prettyHexMessage(msg))
                self.publishStatus("CurrentDemand")
                self.Tcp.transmit(msg)  
                self.enterState(stateWaitForFlexibleRequest) # todo: not clear, what is specified in DIN     
            if (strConverterResult.find("WeldingDetectionReq")>0):
                # todo: check the request content, and fill response parameters
                msg = addV2GTPHeader(exiEncode("EDj")) # EDj for Encode, Din, WeldingDetectionRes
                self.addToTrace("responding " + prettyHexMessage(msg))
                self.publishStatus("WeldingDetection")
                self.Tcp.transmit(msg)  
                self.enterState(stateWaitForFlexibleRequest) # todo: not clear, what is specified in DIN     
            if (strConverterResult.find("SessionStopReq")>0):
                # todo: check the request content, and fill response parameters
                msg = addV2GTPHeader(exiEncode("EDk")) # EDk for Encode, Din, SessionStopRes
                self.addToTrace("responding " + prettyHexMessage(msg))
                self.publishStatus("SessionStop")
                self.Tcp.transmit(msg)  
                self.enterState(stateWaitForFlexibleRequest) # todo: not clear, what is specified in DIN     


                
        if (self.isTooLong()):
            self.enterState(0)
            
    def stateFunctionWaitForChargeParameterDiscoveryRequest(self):
        if (self.isTooLong()):
            self.enterState(0)
    
    def stateFunctionWaitForCableCheckRequest(self):
        if (self.isTooLong()):
            self.enterState(0)
            
    def stateFunctionWaitForPreChargeRequest(self):
        if (self.isTooLong()):
            self.enterState(0)
            
    def stateFunctionWaitForPowerDeliveryRequest(self):
        if (len(self.rxData)>0):
            self.addToTrace("In state WaitForPowerDeliveryRequest, received " + prettyHexMessage(self.rxData))
            self.addToTrace("Todo: Reaction in state WaitForPowerDeliveryRequest is not implemented yet.")
            self.rxData = []
            self.enterState(0)
        if (self.isTooLong()):
            self.enterState(0)
            
       
    stateFunctions = { 
            stateWaitForSupportedApplicationProtocolRequest: stateFunctionWaitForSupportedApplicationProtocolRequest,
            stateWaitForSessionSetupRequest: stateFunctionWaitForSessionSetupRequest,
            stateWaitForServiceDiscoveryRequest: stateFunctionWaitForServiceDiscoveryRequest,
            stateWaitForServicePaymentSelectionRequest: stateFunctionWaitForServicePaymentSelectionRequest,
            stateWaitForFlexibleRequest: stateFunctionWaitForFlexibleRequest,
            stateWaitForChargeParameterDiscoveryRequest: stateFunctionWaitForChargeParameterDiscoveryRequest,
            stateWaitForCableCheckRequest: stateFunctionWaitForCableCheckRequest,
            stateWaitForPreChargeRequest: stateFunctionWaitForPreChargeRequest,
            stateWaitForPowerDeliveryRequest: stateFunctionWaitForPowerDeliveryRequest,
        }
        
    def reInit(self):
        self.addToTrace("re-initializing fsmEvse") 
        self.state = 0
        self.cyclesInState = 0
        self.rxData = []
        self.simulatedPresentVoltage = 0
        self.Tcp.resetTheConnection()
        
    def socketStateNotification(self, notification):
        if (notification==0):
            # The TCP informs us, that the connection is broken.
            # Let's restart the state machine.
            self.publishStatus("TCP conn broken")
            self.addToTrace("re-initializing fsmEvse due to broken connection")
            self.reInit()
        if (notification==1):
            # The TCP informs us, that it is listening, means waiting for incoming connection.
            self.publishStatus("Listening TCP")
        if (notification==2):
            # The TCP informs us, that a connection is established.
            self.publishStatus("TCP connected")

    def __init__(self, addressManager, callbackAddToTrace, hardwareInterface, callbackShowStatus):
        self.callbackAddToTrace = callbackAddToTrace
        self.callbackShowStatus = callbackShowStatus
        #todo self.addressManager = addressManager
        #todo self.hardwareInterface = hardwareInterface
        self.addToTrace("initializing fsmEvse") 
        self.faultInjectionDelayUntilSocketOpen_s = 0
        if (self.faultInjectionDelayUntilSocketOpen_s>0):
            self.addToTrace("Fault injection: waiting " + str(self.faultInjectionDelayUntilSocketOpen_s) + " s until opening the TCP socket.")
            time.sleep(self.faultInjectionDelayUntilSocketOpen_s)
        self.Tcp = pyPlcTcpSocket.pyPlcTcpServerSocket(self.callbackAddToTrace, self.socketStateNotification)
        self.state = 0
        self.cyclesInState = 0
        self.rxData = []
                
    def mainfunction(self):
        self.Tcp.mainfunction() # call the lower-level worker
        if (self.Tcp.isRxDataAvailable()):
                self.rxData = self.Tcp.getRxData()
                #self.addToTrace("received " + str(self.rxData))
        # run the state machine:
        self.cyclesInState += 1 # for timeout handling, count how long we are in a state
        self.stateFunctions[self.state](self)
                
                
if __name__ == "__main__":
    print("Testing the evse state machine")
    evse = fsmEvse()
    print("Press Ctrl-Break for aborting")
    while (True):
        time.sleep(0.1)
        evse.mainfunction()
        

