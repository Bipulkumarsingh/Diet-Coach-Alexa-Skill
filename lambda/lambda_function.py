# -*- coding: utf-8 -*-

# This sample demonstrates handling intents from an Alexa skill using the Alexa Skills Kit SDK for Python.
# Please visit https://alexa.design/cookbook for additional examples on implementing slots, dialog management,
# session persistence, api calls, and more.
# This sample is built using the handler classes approach in skill builder.
import os
import pytz
import boto3
import logging
import datetime
from dialect import *
import ask_sdk_core.utils as ask_utils

# from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.api_client import DefaultApiClient
from ask_sdk_core.skill_builder import CustomSkillBuilder
from ask_sdk_dynamodb.adapter import DynamoDbAdapter
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model.intent import Intent
from ask_sdk_model.dialog import delegate_directive
# from ask_sdk_model.dialog import ElicitSlotDirective
from ask_sdk_model.services.reminder_management import (Trigger, TriggerType,
                                                        AlertInfo,
                                                        SpokenInfo,
                                                        SpokenText,
                                                        PushNotification,
                                                        PushNotificationStatus,
                                                        ReminderRequest,
                                                        Recurrence)

from ask_sdk_model import Response
from ask_sdk_model.interfaces.connections import SendRequestDirective
from ask_sdk_model.services.service_exception import ServiceException
from ask_sdk_model.ui import SimpleCard



logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

REQUIRED_PERMISSIONS = ["alexa::alerts:reminders:skill:readwrite"]
TIME_ZONE_ID= 'America/Los_Angeles'

# Defining the database region, table name and dynamodb persistence adapter
ddb_region = os.environ.get('DYNAMODB_PERSISTENCE_REGION')
ddb_table_name = os.environ.get('DYNAMODB_PERSISTENCE_TABLE_NAME')
ddb_resource = boto3.resource('dynamodb', region_name=ddb_region)
dynamodb_adapter = DynamoDbAdapter(table_name=ddb_table_name, create_table=False, dynamodb_resource=ddb_resource)


def create_diet_reminder(minute_val, reminder_message, reminder_freq):
    now = datetime.datetime.now(pytz.timezone(TIME_ZONE_ID))
    two_mins_from_now = now + datetime.timedelta(minutes=+minute_val)
    notification_time = two_mins_from_now.strftime("%Y-%m-%dT%H:%M:%S")
    
    recurrence_pattern = [
       f"FREQ={reminder_freq[0]};BYHOUR={reminder_freq[1]};BYMINUTE=10;BYSECOND=0;INTERVAL=1;"
    ]
    

    trigger = Trigger(object_type = TriggerType.SCHEDULED_ABSOLUTE ,
     scheduled_time = notification_time ,time_zone_id = TIME_ZONE_ID, recurrence = Recurrence(recurrence_rules=recurrence_pattern))
    
    text = SpokenText(locale='en-US',
     ssml = f"<speak>{reminder_message}</speak>",
      text= reminder_message)
    
    alert_info = AlertInfo(SpokenInfo([text]))
    push_notification = PushNotification(PushNotificationStatus.ENABLED)
    reminder_request = ReminderRequest(notification_time, trigger, alert_info, push_notification)
    
    return reminder_request


class LaunchRequestHandler(AbstractRequestHandler):
    """Handler for Skill Launch."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool

        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        
        attribute_manager = handler_input.attributes_manager
        session_attr = attribute_manager.session_attributes
        persistent_attributes = attribute_manager.persistent_attributes
        
        session_attr['intent'] = "LaunchRequest"
        
        previous_color = persistent_attributes.get('color')
        
        speak_output = GREETING_MESSAGE
        
        if previous_color:
            speak_output += FIRST_TIME
            
            return handler_input.response_builder.speak(speak_output).add_directive(
                delegate_directive.DelegateDirective(
                    updated_intent=Intent(name="CalBmiIntent"))).response
            
        else:
            speak_output += FAV_COLOR

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

class PickColorIntentHanlder(AbstractRequestHandler):
    """Handler for Pick Color Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("PickColorIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        slots = handler_input.request_envelope.request.intent.slots
        attribute_manager = handler_input.attributes_manager
        session_attr = attribute_manager.session_attributes
        persistent_attributes = attribute_manager.persistent_attributes
            
        session_attr['intent'] = "PickColorIntent"
            
        color = slots['color'].value
        color = color.lower()
        logger.info(f"color name: {color}")
        quality = COLOR_QUALITY[color][0]

        # saving color value in db
        # persistent_attributes.update({
        #     "color": color
        # })
        
        persistent_attributes['color'] = color
        handler_input.attributes_manager.save_persistent_attributes()
            
        speak_output = COLOR_PICKED.format(color=color, quality=quality)

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask("Is this your first time here?")
                .response
        )

class CalBmiIntentHandler(AbstractRequestHandler):
    """Handles the intent to calculte the bmi index"""
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("CalBmiIntent")(handler_input)
        
    def handle(self, handler_input):
        try:
            slots = handler_input.request_envelope.request.intent.slots
            attribute_manager = handler_input.attributes_manager
            session_attr = attribute_manager.session_attributes
            
            session_attr['intent'] = "CalBmiIntent"
            
            age = slots['age'].value
            height = slots['height'].value
            weight = slots['weight'].value
            
            bmi = (703*int(weight))/(int(height)*int(height))
            bmi = round(bmi, 2)
            
            speak_output = f"According to my calculations your bmi index is {bmi}. Technically, that is considered "
            
            # check bmi status
            # bmi_descriptor = {
            #     "Underweight": [["<20.7", "men"], ["<19.1", "women"]],
            #     "Normal": [["20.7 - 26.4", "men"], ["19.1 - 25.8", "women"]],
            #     "Marginally Overweight": [["26.4 - 27.8"], ["25.8 - 27.3"]],
            #     "Overweight": [["27.8 - 31.1"], ["27.3 - 32.3"]],
            #     "Obese": [["> 31.1"], ["> 32.3"]]
                
            # }
            
            call_user_goal = 1
            
            if bmi < 20.7:
                speak_output += "Underweight. we might have to discuss further via email or phone."
            elif bmi >= 20.7 and bmi <= 26.4:
                call_user_goal = 0
                speak_output += "Healthy, nice job!"
            elif bmi > 26.4 and bmi <= 27.8:
                speak_output += "Overweight."
            elif bmi > 27.8 and bmi <= 31.1:
                speak_output += "Obese."
            elif bmi > 31.1:
                speak_output += "Extremely obese."
            
            if call_user_goal:
                speak_output += AFTER_BMI
                
                return handler_input.response_builder.speak(speak_output).add_directive(
                delegate_directive.DelegateDirective(
                    updated_intent=Intent(name="UserGoalsIntent"))).response
            else:
                speak_output += f"{BEFORE_LAST_WORDS} {INTERESTED_WORD}"
        except Exception as e:
            e = str(e)
            logger.exception(e)
            speak_output = ERROR_MESSAGE
        return (
        handler_input.response_builder
            .speak(speak_output)
            .ask(INTERESTED_WORD)
            .response)

class UserGoalsIntentHandler(AbstractRequestHandler):
    """Handle the intent to store users goals"""
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("UserGoalsIntent")(handler_input)
        
    def handle(self, handler_input):
        try:
            slots = handler_input.request_envelope.request.intent.slots
            attribute_manager = handler_input.attributes_manager
            session_attr = attribute_manager.session_attributes
            
            session_attr["intent"] = "UserGoalsIntent"
            
            weight = slots['weight'].value
            months = slots['months'].value
            
            logger.info(f"weight to lose: {weight},\n num of months: {months}")
            
            speak_output = f"{HEALTH_GOAL} {BEFORE_LAST_WORDS} {INTERESTED_WORD}"
            
        except Exception as e:
            e = str(e)
            logger.exception(e)
            speak_output = ERROR_MESSAGE
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(INTERESTED_WORD)
                .response)


class ChatIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("ChatIntent")(handler_input)
        
    def handle(self, handler_input):
        slots = handler_input.request_envelope.request.intent.slots
        
        option = slots['option'].value
        option = option.lower()
        
        logger.info(f"chat value: {option}")
        
        speak_output = CHAT_TYPE.get(option, "Great")
        speak_output += AFTER_CHAT
        # repromt = "How would you like to chat, via email or phone or continue like this say 1, 2 or 3"
        # return (
        #     handler_input.response_builder
        #         .speak(speak_output)
        #         # .ask(repromt)
        #         .response)
        return handler_input.response_builder.speak(speak_output).add_directive(
            delegate_directive.DelegateDirective(
                updated_intent=Intent(name="CalBmiIntent"))).response
    
class YesIntentHandler(AbstractRequestHandler):
    """Handler for yes responses"""
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("AMAZON.YesIntent")(handler_input)
        
    def handle(self, handler_input):
        try:
            attribute_manager = handler_input.attributes_manager
            session_attr = attribute_manager.session_attributes
            persistent_attributes = attribute_manager.persistent_attributes
            
            previous_intent = session_attr.get('intent')
            
            if previous_intent == "PickColorIntent":
                speak_output = FIRST_TIME
                
                return handler_input.response_builder.speak(speak_output).add_directive(
                delegate_directive.DelegateDirective(
                    updated_intent=Intent(name="CalBmiIntent"))).response
            
            elif previous_intent == "WorryHandler":
                session_attr['worry'] = True
                speak_output = "Thank You!"
                speak_output += AFTER_WORRY
                
                return handler_input.response_builder.speak(speak_output).add_directive(
                delegate_directive.DelegateDirective(
                    updated_intent=Intent(name="ChatIntent"))).response
            
            elif previous_intent in ("CalBmiIntent", "UserGoalsIntent"):
                session_attr['intent'] = "GoodByeIntent"
                
                previous_color = persistent_attributes.get('color')
                quality = COLOR_QUALITY[previous_color][0]
                bye_word = COLOR_QUALITY[previous_color][1]
                
                speak_output = "Great! if you have any issues, please email or call me. "
                speak_output += LAST_WORDS.format(color_quality=quality, bye_word=bye_word)

                if persistent_attributes.get('reminder'):
                    return (handler_input.response_builder
                    .speak(speak_output)
                    .set_should_end_session(True)
                    .response)
                else:
                    speak_output += REMINDER_MESSAGE
                    
                    return handler_input.response_builder.speak(speak_output).add_directive(
                    delegate_directive.DelegateDirective(
                        updated_intent=Intent(name="ReminderHelperIntent"))).response
            elif previous_intent == "GoodByeIntent":
                speak_output = "THANK YOU!"
                
                return handler_input.response_builder.speak(speak_output).add_directive(
                    delegate_directive.DelegateDirective(
                    updated_intent=Intent(name="ReminderIntent"))).response
                
            else:
                speak_output = ERROR_MESSAGE
            
            
        except Exception as e:
            e = str(e)
            logger.exception(e)
            speak_output = ERROR_MESSAGE
        return (
            handler_input.response_builder
                .speak(speak_output)
                # .ask(speak_output)
                .response)

class NoIntentHandler(AbstractRequestHandler):
    """Handler for yes responses"""
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("AMAZON.NoIntent")(handler_input)
        
    def handle(self, handler_input):
        try:
            attribute_manager = handler_input.attributes_manager
            session_attr = attribute_manager.session_attributes
            persistent_attributes = attribute_manager.persistent_attributes
            
            previous_intent = session_attr.get('intent')
            
            logger.info(f"Previous intent inside no intent: {previous_intent}")
            
            if previous_intent == "PickColorIntent":
                speak_output = NOT_FIRST_TIME
                session_attr['intent'] = "WorryHandler"
                
                return handler_input.response_builder.speak(speak_output).add_directive(
                delegate_directive.DelegateDirective(
                    updated_intent=Intent(name="WorryIntent"))).response
            
            elif previous_intent == "WorryHandler":
                session_attr['worry'] = False
                speak_output = "Ok, No Problem, Maybe next time."
                speak_output += AFTER_WORRY
                
                return handler_input.response_builder.speak(speak_output).add_directive(
                delegate_directive.DelegateDirective(
                    updated_intent=Intent(name="ChatIntent"))).response
            
            elif previous_intent in ("CalBmiIntent", "UserGoalsIntent"):
                session_attr['intent'] = "GoodByeIntent"
                
                previous_color = persistent_attributes.get('color')
                quality = COLOR_QUALITY[previous_color][0]
                bye_word = COLOR_QUALITY[previous_color][1]
                
                logger.info(f"Previous saved color: {previous_color} {quality} {bye_word}")
                
                speak_output = "No problem, if you change your mind, feel free to email or call me, and i can offer you a significant discount. "
                speak_output += LAST_WORDS.format(color_quality=quality, bye_word=bye_word)
                
                if persistent_attributes.get('reminder'):
                    return (handler_input.response_builder
                    .speak(speak_output)
                    .set_should_end_session(True)
                    .response)
                else:
                    speak_output += REMINDER_MESSAGE
                    
                    return handler_input.response_builder.speak(speak_output).add_directive(
                        delegate_directive.DelegateDirective(
                            updated_intent=Intent(name="ReminderHelperIntent"))).response
            elif previous_intent == "GoodByeIntent":
                speak_output = "OK, NO PROBLEM, MAYBE NEXT TIME."
                
                return (
                    handler_input.response_builder
                        .speak(speak_output)
                        .set_should_end_session(True)
                        .response
                    )
                        
            else:
                speak_output = ERROR_MESSAGE
            
        except Exception as e:
            e = str(e)
            logger.exception(e)
            speak_output = ERROR_MESSAGE
        return (
            handler_input.response_builder
                .speak(speak_output)
                # .ask(speak_output)
                .response)


class ReminderIntentHandler(AbstractRequestHandler):
    """Handler for Hello World Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("ReminderIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("Reminder Intent handler")
        request_envelope = handler_input.request_envelope
        response_builder = handler_input.response_builder
        reminder_service = handler_input.service_client_factory.get_reminder_management_service()
        permissions = handler_input.request_envelope.context.system.user.permissions
        persistent_attributes = handler_input.attributes_manager.persistent_attributes

        if not (permissions and permissions.consent_token):
            # return response_builder.speak(NOTIFY_MISSING_PERMISSIONS).set_card(
            #     AskForPermissionsConsentCard(permissions=PERMISSIONS)).response
            
            return response_builder.add_directive(
                SendRequestDirective(
                    name="AskFor",
                    payload={
                        "@type": "AskForPermissionsConsentRequest",
                        "@version": "1",
                        "permissionScope": "alexa::alerts:reminders:skill:readwrite"
                    },
                    token="correlationToken"
                )
            ).response
        
        daily_1 = create_diet_reminder(2, DAILY_REMINDER, ["DAILY", "6"])
        weekly_1 = create_diet_reminder(4, WEEKLY_REMINDER_1, ["WEEKLY", "7"])
        weekly_2 = create_diet_reminder(6, WEEKLY_REMINDER_2, ["WEEKLY", "8"])
        weekly_3 = create_diet_reminder(8, WEEKLY_REMINDER_3, ["WEEKLY", "9"])
        weekly_4 = create_diet_reminder(10, WEEKLY_REMINDER_4, ["WEEKLY", "10"])
        
        try:
            reminder_response = reminder_service.create_reminder([daily_1, weekly_1, weekly_2, weekly_3, weekly_4])
            logger.info("Reminder Created: {}".format(reminder_response))
            
            persistent_attributes['reminder'] = True
            handler_input.attributes_manager.save_persistent_attributes()
        except ServiceException as e:
            logger.info("Exception encountered: {}".format(e.body))
            return response_builder.speak(ERROR_MESSAGE).response

        return response_builder.speak("Your diet reminder created").set_card(
            SimpleCard("Diet Reminder" , "Diet Reminder created")).set_should_end_session(True).response


class DeleteColorIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("DeleteColorIntent")(handler_input)
    
    def handle(self,handler_input):
        
        # Delete all attributes from the DB
        handler_input.attributes_manager.delete_persistent_attributes()
        
        speech_output = "your color details are deleted now!"
        
        return(
            handler_input.response_builder
                .speak(speech_output)
                # .ask(reprompt)
                .response
            )

class WorryIntentHandler(AbstractRequestHandler):
    """Handler for Hello World Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("WorryIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        slots = handler_input.request_envelope.request.intent.slots
        attribute_manager = handler_input.attributes_manager
        session_attr = attribute_manager.session_attributes
        
        worry_resp = slots['worry'].value
        
        session_attr['worry'] = True
        if worry_resp in ('yes', 'sure', 'ok'):
            speak_output = "THANK YOU!"
        else:
            speak_output = "OK, NO PROBLEM, MAYBE NEXT TIME."
        
        speak_output += AFTER_WORRY
                
        return handler_input.response_builder.speak(speak_output).add_directive(
                delegate_directive.DelegateDirective(
                    updated_intent=Intent(name="ChatIntent"))).response

class ReminderHelperIntentHandler(AbstractRequestHandler):
    """Handler for Hello World Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("ReminderHelperIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        slots = handler_input.request_envelope.request.intent.slots
        
        reminder_resp = slots['reminder_option'].value
        
        
        if reminder_resp in ('yes', 'sure', 'ok'):
            speak_output = "THANK YOU!"
            
            return handler_input.response_builder.speak(speak_output).add_directive(
                delegate_directive.DelegateDirective(
                    updated_intent=Intent(name="ReminderIntent"))).response
        else:
            speak_output = "OK, NO PROBLEM, MAYBE NEXT TIME."
            
            return (
            handler_input.response_builder
                .speak(speak_output)
                .set_should_end_session(True)
                .response
            )


# class HelloWorldIntentHandler(AbstractRequestHandler):
#     """Handler for Hello World Intent."""
#     def can_handle(self, handler_input):
#         # type: (HandlerInput) -> bool
#         return ask_utils.is_intent_name("HelloWorldIntent")(handler_input)

#     def handle(self, handler_input):
#         # type: (HandlerInput) -> Response
#         speak_output = "Hello World!"

#         return (
#             handler_input.response_builder
#                 .speak(speak_output)
#                 # .ask("add a reprompt if you want to keep the session open for the user to respond")
#                 .response
#         )


class HelpIntentHandler(AbstractRequestHandler):
    """Handler for Help Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "You can say hello to me! How can I help?"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class CancelOrStopIntentHandler(AbstractRequestHandler):
    """Single handler for Cancel and Stop Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input) or
                ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Goodbye!"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .response
        )

class FallbackIntentHandler(AbstractRequestHandler):
    """Single handler for Fallback Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In FallbackIntentHandler")
        speech = "Hmm, I'm not sure. You can say Hello or Help. What would you like to do?"
        reprompt = "I didn't catch that. What can I help you with?"

        return handler_input.response_builder.speak(speech).ask(reprompt).response

class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler for Session End."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        # Any cleanup logic goes here.

        return handler_input.response_builder.response


class IntentReflectorHandler(AbstractRequestHandler):
    """The intent reflector is used for interaction model testing and debugging.
    It will simply repeat the intent the user said. You can create custom handlers
    for your intents by defining them above, then also adding them to the request
    handler chain below.
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("IntentRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        intent_name = ask_utils.get_intent_name(handler_input)
        speak_output = "You just triggered " + intent_name + "."

        return (
            handler_input.response_builder
                .speak(speak_output)
                # .ask("add a reprompt if you want to keep the session open for the user to respond")
                .response
        )


class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Generic error handling to capture any syntax or routing errors. If you receive an error
    stating the request handler chain is not found, you have not implemented a handler for
    the intent being invoked or included it in the skill builder below.
    """
    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        logger.error(exception, exc_info=True)

        speak_output = "Sorry, I had trouble doing what you asked. Please try again."

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

# The SkillBuilder object acts as the entry point for your skill, routing all request and response
# payloads to the handlers above. Make sure any new handlers or interceptors you've
# defined are included below. The order matters - they're processed top to bottom.


# sb = SkillBuilder()
sb = CustomSkillBuilder(persistence_adapter = dynamodb_adapter, api_client=DefaultApiClient())

sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(ReminderIntentHandler())
sb.add_request_handler(PickColorIntentHanlder())
sb.add_request_handler(CalBmiIntentHandler())
sb.add_request_handler(UserGoalsIntentHandler())
sb.add_request_handler(ChatIntentHandler())
sb.add_request_handler(YesIntentHandler())
sb.add_request_handler(NoIntentHandler())
sb.add_request_handler(WorryIntentHandler())
sb.add_request_handler(ReminderIntentHandler())
sb.add_request_handler(ReminderHelperIntentHandler())
sb.add_request_handler(DeleteColorIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(IntentReflectorHandler()) # make sure IntentReflectorHandler is last so it doesn't override your custom intent handlers

sb.add_exception_handler(CatchAllExceptionHandler())

lambda_handler = sb.lambda_handler()