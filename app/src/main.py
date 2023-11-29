# Copyright (c) 2022 Robert Bosch GmbH and Microsoft Corporation
#
# This program and the accompanying materials are made available under the
# terms of the Apache License, Version 2.0 which is available at
# https://www.apache.org/licenses/LICENSE-2.0.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# SPDX-License-Identifier: Apache-2.0

"""A sample skeleton vehicle app."""

import asyncio
import json
import logging
import signal

from vehicle import Vehicle, vehicle  # type: ignore
from velocitas_sdk.util.log import (  # type: ignore
    get_opentelemetry_log_factory,
    get_opentelemetry_log_format,
)
from velocitas_sdk.vdb.reply import DataPointReply
from velocitas_sdk.vehicle_app import VehicleApp, subscribe_topic

# Configure the VehicleApp logger with the necessary log config and level.
logging.setLogRecordFactory(get_opentelemetry_log_factory())
logging.basicConfig(format=get_opentelemetry_log_format())
logging.getLogger().setLevel("DEBUG")
logger = logging.getLogger(__name__)

GET_SCORE_REQUEST_TOPIC = "sampleapp/getScore"
GET_SCORE_RESPONSE_TOPIC = "sampleapp/getScore/response"

DATABROKER_SPEED_SUBSCRIPTION_TOPIC = "sampleapp/currentSpeed"
DATABROKER_STEER_SUBSCRIPTION_TOPIC = "sampleapp/currentSteer"
DATABROKER_TRHOT_SUBSCRIPTION_TOPIC = "sampleapp/currentThrottle"
DATABROKER_BRAKE_SUBSCRIPTION_TOPIC = "sampleapp/currentBrake"
DATABROKER_LANE_SUBSCRIPTION_TOPIC = "sampleapp/currentLane"


class SampleApp(VehicleApp):
    """
    Sample skeleton vehicle app.

    The skeleton subscribes to a getSpeed MQTT topic
    to listen for incoming requests to get
    the current vehicle speed and publishes it to
    a response topic.

    It also subcribes to the VehicleDataBroker
    directly for updates of the
    Vehicle.Speed signal and publishes this
    information via another specific MQTT topic
    """

    def __init__(self, vehicle_client: Vehicle):
        # SampleApp inherits from VehicleApp.
        super().__init__()
        self.Vehicle = vehicle_client

    async def on_start(self):
        """Run when the vehicle app starts"""
        # This method will be called by the SDK when the connection to the
        # Vehicle DataBroker is ready.
        # Here you can subscribe for the Vehicle Signals update (e.g. Vehicle Speed).
        await self.Vehicle.Speed.subscribe(self.on_speed_change)
        await self.Vehicle.Chassis.SteeringWheel.Angle.subscribe(self.on_steer_change)
        await self.Vehicle.OBD.ThrottlePosition.subscribe(self.on_throttle_change)
        await self.Vehicle.Chassis.Brake.PedalPosition.subscribe(self.on_brake_change)
        await self.Vehicle.ADAS.LaneDepartureDetection.IsWarning.subscribe(
            self.on_lane_change
        )

    async def on_speed_change(self, data: DataPointReply):
        """The on_speed_change callback, this will be executed when receiving a new
        vehicle signal updates."""
        # Get the current vehicle speed value from the received DatapointReply.
        # The DatapointReply containes the values of all subscribed DataPoints of
        # the same callback.
        vehicle_speed = data.get(self.Vehicle.Speed).value

        # Do anything with the received value.
        # Example:
        # - Publishes current speed to MQTT Topic (i.e. DATABROKER_SUBSCRIPTION_TOPIC).
        await self.publish_event(
            DATABROKER_SPEED_SUBSCRIPTION_TOPIC,
            json.dumps({"speed": vehicle_speed}),
        )

    async def on_steer_change(self, data: DataPointReply):
        steering_angle = data.get(self.Vehicle.Chassis.SteeringWheel.Angle).value
        await self.publish_event(
            DATABROKER_STEER_SUBSCRIPTION_TOPIC,
            json.dumps({"steeringAngle": steering_angle}),
        )

    # 스로틀 위치 변경에 대한 콜백 메서드
    async def on_throttle_change(self, data: DataPointReply):
        throttle_position = data.get(self.Vehicle.OBD.ThrottlePosition).value
        await self.publish_event(
            DATABROKER_TRHOT_SUBSCRIPTION_TOPIC,
            json.dumps({"throttlePosition": throttle_position}),
        )

    # 브레이크 위치 변경에 대한 콜백 메서드
    async def on_brake_change(self, data: DataPointReply):
        brake = data.get(self.Vehicle.Chassis.Brake.PedalPosition).value
        await self.publish_event(
            DATABROKER_BRAKE_SUBSCRIPTION_TOPIC,
            json.dumps({"brakePosition": brake}),
        )

    # 차선 이탈 경고 변경에 대한 콜백 메서드
    async def on_lane_change(self, data: DataPointReply):
        lane = data.get(self.Vehicle.ADAS.LaneDepartureDetection.IsWarning).value
        await self.publish_event(
            DATABROKER_LANE_SUBSCRIPTION_TOPIC,
            json.dumps({"laneWarning": lane}),
        )

    @subscribe_topic(GET_SCORE_REQUEST_TOPIC)
    async def on_get_score_request_received(self, data: str) -> None:
        """The subscribe_topic annotation is used to subscribe for incoming
        PubSub events, e.g. MQTT event for GET_SCORE_REQUEST_TOPIC.
        """

        # Use the logger with the preferred log level (e.g. debug, info, error, etc)
        logger.debug(
            "PubSub event for the Topic: %s -> is received with the data: %s",
            GET_SCORE_REQUEST_TOPIC,
            data,
        )

        # Getting current speed from VehicleDataBroker using the DataPoint getter.
        driving_score = (await self.Vehicle.Speed.get()).value

        # Do anything with the speed value.
        # Example:
        # - Publishes the vehicle speed to MQTT topic (i.e. GET_SPEED_RESPONSE_TOPIC).
        await self.publish_event(
            GET_SCORE_RESPONSE_TOPIC,
            json.dumps(
                {
                    "result": {
                        "status": 0,
                        "message": f"""Current Score = {driving_score}""",
                    },
                }
            ),
        )


async def main():
    """Main function"""
    logger.info("Starting SampleApp...")
    # Constructing SampleApp and running it.
    vehicle_app = SampleApp(vehicle)
    await vehicle_app.run()


LOOP = asyncio.get_event_loop()
LOOP.add_signal_handler(signal.SIGTERM, LOOP.stop)
LOOP.run_until_complete(main())
LOOP.close()
