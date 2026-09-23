from datetime import datetime
from zoneinfo import available_timezones

from rest_framework import serializers

MAX_LABEL_LEN = 200
START_TIME_FORMAT = "%Y-%m-%dT%H:%M"
MINUTE_STEP_MIN = 15  # A-10
CYCLE_STEP_HRS = 0.25


class LocationSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=MAX_LABEL_LEN, allow_blank=False)
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lng = serializers.FloatField(min_value=-180, max_value=180)


class LogMetaSerializer(serializers.Serializer):
    driver_name = serializers.CharField(max_length=MAX_LABEL_LEN, required=False)
    co_driver_name = serializers.CharField(
        max_length=MAX_LABEL_LEN, required=False, allow_blank=True
    )
    carrier_name = serializers.CharField(max_length=MAX_LABEL_LEN, required=False)
    main_office_address = serializers.CharField(max_length=MAX_LABEL_LEN, required=False)
    home_terminal_address = serializers.CharField(max_length=MAX_LABEL_LEN, required=False)
    truck_tractor_no = serializers.CharField(max_length=MAX_LABEL_LEN, required=False)
    trailer_no = serializers.CharField(max_length=MAX_LABEL_LEN, required=False)
    shipping_doc_no = serializers.CharField(max_length=MAX_LABEL_LEN, required=False)
    shipper_commodity = serializers.CharField(max_length=MAX_LABEL_LEN, required=False)


class TripRequestSerializer(serializers.Serializer):
    current = LocationSerializer()
    pickup = LocationSerializer()
    dropoff = LocationSerializer()
    cycle_used_hrs = serializers.FloatField(min_value=0, max_value=70)  # R-04
    start_time = serializers.CharField(required=False, allow_null=True)
    home_timezone = serializers.CharField(required=False, allow_null=True)
    include_inspections = serializers.BooleanField(required=False)
    log_meta = LogMetaSerializer(required=False)

    def validate_cycle_used_hrs(self, value):
        steps = value / CYCLE_STEP_HRS
        if abs(steps - round(steps)) > 1e-6:
            raise serializers.ValidationError("cycle_used_hrs must be in 0.25-hour increments.")
        return value

    def validate_start_time(self, value):
        if value is None:
            return value
        try:
            parsed = datetime.strptime(value, START_TIME_FORMAT)
        except ValueError:
            raise serializers.ValidationError(
                'start_time must match the format "YYYY-MM-DDTHH:MM".'
            ) from None
        if parsed.minute % MINUTE_STEP_MIN != 0:  # A-10
            raise serializers.ValidationError("start_time minutes must be a multiple of 15.")
        return value

    def validate_home_timezone(self, value):
        if value is None:
            return value
        if value not in available_timezones():
            raise serializers.ValidationError(f"Unknown timezone: {value}.")
        return value


class RouteLegSerializer(serializers.Serializer):
    distance_mi = serializers.FloatField()
    duration_hrs = serializers.FloatField()

    def get_fields(self):
        fields = super().get_fields()
        fields["from"] = serializers.CharField()
        fields["to"] = serializers.CharField()
        return fields


class RouteGeometrySerializer(serializers.Serializer):
    type = serializers.CharField()
    coordinates = serializers.ListField(child=serializers.ListField(child=serializers.FloatField()))


class RouteSerializer(serializers.Serializer):
    geometry = RouteGeometrySerializer()
    legs = RouteLegSerializer(many=True)


class StopSerializer(serializers.Serializer):
    seq = serializers.IntegerField()
    type = serializers.ChoiceField(
        choices=["pickup", "fuel", "break_30", "rest_10", "restart_34", "dropoff"]
    )
    label = serializers.CharField()
    lat = serializers.FloatField()
    lng = serializers.FloatField()
    mile_marker = serializers.FloatField()
    arrive_at = serializers.CharField()
    depart_at = serializers.CharField()
    duration_min = serializers.IntegerField()
    status = serializers.ChoiceField(choices=["OFF", "SB", "D", "ON"])


class LogHeaderSerializer(serializers.Serializer):
    miles_driving_today = serializers.FloatField()
    total_mileage_today = serializers.FloatField()
    driver_name = serializers.CharField()
    co_driver_name = serializers.CharField(allow_blank=True)
    carrier_name = serializers.CharField()
    main_office_address = serializers.CharField()
    home_terminal_address = serializers.CharField()
    truck_tractor_no = serializers.CharField()
    trailer_no = serializers.CharField()
    shipping_doc_no = serializers.CharField()
    shipper_commodity = serializers.CharField()

    def get_fields(self):
        fields = super().get_fields()
        fields["from"] = serializers.CharField()
        fields["to"] = serializers.CharField()
        return fields


class DutySegmentSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["OFF", "SB", "D", "ON"])
    start_min = serializers.IntegerField()
    end_min = serializers.IntegerField()
    note = serializers.CharField(allow_null=True)
    location = serializers.CharField(allow_null=True)


class DutyTotalsSerializer(serializers.Serializer):
    OFF = serializers.FloatField()
    SB = serializers.FloatField()
    D = serializers.FloatField()
    ON = serializers.FloatField()


class RemarkSerializer(serializers.Serializer):
    at_min = serializers.IntegerField()
    location = serializers.CharField(allow_null=True)
    note = serializers.CharField(allow_null=True)


class RecapSerializer(serializers.Serializer):
    on_duty_today = serializers.FloatField()
    a_last_7 = serializers.FloatField()
    b_available_tomorrow = serializers.FloatField()
    c_last_5 = serializers.FloatField()
    restart_34_taken = serializers.BooleanField()


class DailyLogSerializer(serializers.Serializer):
    day_number = serializers.IntegerField()
    date = serializers.CharField()
    header = LogHeaderSerializer()
    segments = DutySegmentSerializer(many=True)
    totals = DutyTotalsSerializer()
    remarks = RemarkSerializer(many=True)
    recap = RecapSerializer()


class TripInputsSerializer(serializers.Serializer):
    current = LocationSerializer()
    pickup = LocationSerializer()
    dropoff = LocationSerializer()
    cycle_used_hrs = serializers.FloatField()
    start_time = serializers.CharField()
    home_timezone = serializers.CharField()
    include_inspections = serializers.BooleanField()
    log_meta = LogMetaSerializer()


class TripSummarySerializer(serializers.Serializer):
    total_miles = serializers.FloatField()
    total_driving_hrs = serializers.FloatField()
    total_on_duty_hrs = serializers.FloatField()
    start_at = serializers.CharField()
    arrive_at = serializers.CharField()
    end_at = serializers.CharField()
    log_days = serializers.IntegerField()
    stop_count = serializers.IntegerField()
    cycle_used_end_hrs = serializers.FloatField()
    home_timezone = serializers.CharField()


class TripResponseSerializer(serializers.Serializer):
    id = serializers.CharField()
    inputs = TripInputsSerializer()
    summary = TripSummarySerializer()
    route = RouteSerializer()
    stops = StopSerializer(many=True)
    daily_logs = DailyLogSerializer(many=True)


class GeocodeResultSerializer(serializers.Serializer):
    label = serializers.CharField()
    lat = serializers.FloatField()
    lng = serializers.FloatField()


class ErrorDetailSerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()
    fields = serializers.DictField(child=serializers.ListField(child=serializers.CharField()))


class ErrorResponseSerializer(serializers.Serializer):
    error = ErrorDetailSerializer()
