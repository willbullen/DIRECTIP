"""
Django management command to reprocess existing EUCAWS payloads

Usage:
    python manage.py reprocess_eucaws
    python manage.py reprocess_eucaws --limit 100
    python manage.py reprocess_eucaws --dry-run
"""

from django.core.management.base import BaseCommand
from receiver.models import SatelliteData
from receiver.eucaws_decoder import decode_eucaws_payload


class Command(BaseCommand):
    help = 'Reprocess existing EUCAWS payloads with the updated decoder'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit number of records to process'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without saving'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Reprocess all records, even those already decoded'
        )

    def handle(self, *args, **options):
        limit = options['limit']
        dry_run = options['dry_run']
        force = options['force']

        # Query for records with 30-byte payloads
        queryset = SatelliteData.objects.filter(payload_hex__isnull=False)
        
        if not force:
            # Only process records that haven't been successfully decoded yet
            queryset = queryset.filter(is_eucaws_decoded=False)
        
        queryset = queryset.order_by('-timestamp')
        
        if limit:
            queryset = queryset[:limit]

        total = queryset.count()
        self.stdout.write(f"Found {total} records to process")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes will be saved"))

        success_count = 0
        error_count = 0
        skipped_count = 0

        for i, record in enumerate(queryset, 1):
            try:
                # Extract payload bytes from hex
                if not record.payload_hex:
                    self.stdout.write(f"[{i}/{total}] Skipping record {record.id} - no payload_hex")
                    skipped_count += 1
                    continue

                payload_bytes = bytes.fromhex(record.payload_hex)

                # Check if it's a 30-byte EUCAWS payload
                if len(payload_bytes) != 30:
                    self.stdout.write(f"[{i}/{total}] Skipping record {record.id} - payload is {len(payload_bytes)} bytes, not 30")
                    skipped_count += 1
                    continue

                # Decode with session_time for date context
                eucaws_data = decode_eucaws_payload(payload_bytes, record.session_time)

                if eucaws_data.get('is_decoded'):
                    # Update record with decoded data
                    if not dry_run:
                        record.eucaws_timestamp = eucaws_data.get('timestamp')
                        record.wind_speed_ms = eucaws_data.get('wind_speed_ms')
                        record.wind_speed_knots = eucaws_data.get('wind_speed_knots')
                        record.wind_direction = eucaws_data.get('wind_direction')
                        record.air_temperature = eucaws_data.get('air_temperature')
                        record.sea_temperature = eucaws_data.get('sea_temperature')
                        record.barometric_pressure = eucaws_data.get('barometric_pressure')
                        record.relative_humidity = eucaws_data.get('relative_humidity')
                        record.is_eucaws_decoded = True
                        record.eucaws_decode_error = None
                        record.save()

                    success_count += 1
                    
                    # Show decoded values
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"[{i}/{total}] ✓ Record {record.id} decoded successfully"
                        )
                    )
                    
                    # Show key values
                    if eucaws_data.get('barometric_pressure'):
                        self.stdout.write(f"  Pressure: {eucaws_data['barometric_pressure']} hPa")
                    if eucaws_data.get('sea_temperature'):
                        self.stdout.write(f"  Sea temp: {eucaws_data['sea_temperature']} °C")
                    if eucaws_data.get('air_temperature'):
                        self.stdout.write(f"  Air temp: {eucaws_data['air_temperature']} °C")
                    
                else:
                    # Decoding failed
                    if not dry_run:
                        record.is_eucaws_decoded = False
                        record.eucaws_decode_error = eucaws_data.get('decode_error', 'Unknown error')
                        record.save()

                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f"[{i}/{total}] ✗ Record {record.id} decode failed: {eucaws_data.get('decode_error')}"
                        )
                    )

            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"[{i}/{total}] ✗ Record {record.id} processing error: {str(e)}"
                    )
                )

        # Summary
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS(f"Processing complete!"))
        self.stdout.write(f"Total processed: {total}")
        self.stdout.write(self.style.SUCCESS(f"Successfully decoded: {success_count}"))
        self.stdout.write(self.style.ERROR(f"Failed: {error_count}"))
        self.stdout.write(f"Skipped: {skipped_count}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("\nDRY RUN - No changes were saved to database"))
