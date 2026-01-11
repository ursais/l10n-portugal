# Copyright 2024 Open Source Integrators
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

"""Tests for l10n_pt_stock_vehicle_daily module."""

from odoo.tests.common import TransactionCase


class TestL10nPtStockVehicleDaily(TransactionCase):
    """Test l10n_pt_stock_vehicle_daily functionality."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Disable tracking for tests as recommended in Odoo 19.0 migration guide
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

    def test_stock_location_license_plate_field(self):
        """Test that license plate field is added to stock.location."""
        # Create a location with license plate
        location = self.env["stock.location"].create(
            {
                "name": "Test Vehicle Location",
                "usage": "internal",
                "l10n_pt_license_plate": "ABC-123",
            }
        )

        self.assertTrue(location.exists())
        self.assertEqual(location.l10n_pt_license_plate, "ABC-123")

    def test_stock_picking_license_plate_computation(self):
        """Test that license plate is computed from location."""
        # Create a location with license plate
        location = self.env["stock.location"].create(
            {
                "name": "Test Vehicle Location",
                "usage": "internal",
                "l10n_pt_license_plate": "XYZ-789",
            }
        )

        # Create a picking for that location
        picking = self.env["stock.picking"].create(
            {
                "location_id": location.id,
                "location_dest_id": self.env.ref("stock.stock_location_stock").id,
                "picking_type_id": self.env.ref("stock.picking_type_internal").id,
            }
        )

        self.assertEqual(picking.l10n_pt_license_plate, "XYZ-789")

    def test_stock_move_location_wizard_extension(self):
        """Test that the wizard extension works correctly."""
        # Create a location with license plate
        location = self.env["stock.location"].create(
            {
                "name": "Test Vehicle Location",
                "usage": "internal",
                "l10n_pt_license_plate": "DEF-456",
            }
        )

        # Create the wizard
        wizard = self.env["wiz.stock.move.location"].create(
            {
                "origin_location_id": location.id,
                "destination_location_id": self.env.ref(
                    "stock.stock_location_stock"
                ).id,
            }
        )

        # Check that license plate is computed
        self.assertEqual(wizard.l10n_pt_license_plate, "DEF-456")

    def test_picking_type_action_move_location_extension(self):
        """Test that picking type action is extended correctly."""
        # Get an internal picking type
        picking_type = self.env.ref("stock.picking_type_internal")

        # Call the action
        action = picking_type.action_move_location()

        # Check that context is set for editing locations
        self.assertTrue(action["context"].get("default_edit_locations", False))

    def test_wizard_creates_picking_with_license_plate(self):
        """Test that wizard creates picking with license plate."""
        # Create a location with license plate
        location = self.env["stock.location"].create(
            {
                "name": "Test Vehicle Location",
                "usage": "internal",
                "l10n_pt_license_plate": "GHI-012",
            }
        )

        # Create the wizard
        wizard = self.env["wiz.stock.move.location"].create(
            {
                "origin_location_id": location.id,
                "destination_location_id": self.env.ref(
                    "stock.stock_location_stock"
                ).id,
            }
        )

        # Create picking
        picking = wizard._create_picking()

        # Check that picking has the license plate
        self.assertEqual(picking.l10n_pt_license_plate, "GHI-012")

    def test_manifest_version_format(self):
        """Test that manifest version follows 19.0 format."""
        manifest = self.env["ir.module.module"].search(
            [("name", "=", "l10n_pt_stock_vehicle_daily")]
        )
        self.assertTrue(manifest.exists())

        # Version should follow 19.0.x.x.x format
        version = manifest.version
        self.assertTrue(version.startswith("19.0."))
        version_parts = version.split(".")
        self.assertEqual(len(version_parts), 4)  # 19.0.1.0.0 format

    def test_tracking_disabled_in_tests(self):
        """Test that tracking is properly disabled in tests."""
        # This test ensures that the test environment has tracking disabled
        # as recommended in the migration guide
        self.assertTrue(self.env.context.get("tracking_disable", False))
