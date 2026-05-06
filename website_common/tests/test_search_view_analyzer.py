# Copyright 2026 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)

import time

from lxml import etree
from odoo.tests.common import TransactionCase, tagged

from ..utils.arch import SearchViewParser


@tagged("search_view_parser")
class TestSearchViewParser(TransactionCase):
    """Test cases for SearchViewParser class"""

    def setUp(self):
        """Set up test data"""
        super().setUp()

        # Simple search view arch
        self.simple_arch = """
        <search>
            <field name="name" string="Name"/>
            <field name="date" string="Date"/>
            <filter name="active" string="Active" domain="[('active', '=', True)]"/>
        </search>
        """

        # Complex search view arch
        self.complex_arch = """
        <search>
            <field name="name" string="Name" filter_domain="[('name', 'ilike', self)]"/>
            <field name="partner_id" string="Partner" operator="child_of"/>
            <field name="date" string="Date" context="{'default_date': self}"/>

            <separator string="Filters"/>
            <filter name="active" string="Active Records" domain="[('active', '=', True)]"/>
            <filter name="inactive" string="Inactive Records" domain="[('active', '=', False)]" help="Show inactive records"/>
            <filter name="recent" string="Recent" domain="[('create_date', '>=', (context_today() - datetime.timedelta(days=7)).strftime('%Y-%m-%d'))]"/>

            <separator/>
            <filter name="date_filter" string="Date Range" date="date" default_period="this_month"/>

            <group expand="0" string="Group By">
                <filter name="group_partner" string="Partner" context="{'group_by': 'partner_id'}"/>
                <filter name="group_date" string="Date" context="{'group_by': 'date'}"/>
            </group>

            <searchpanel>
                <field name="category_id" string="Category" select="multi" enable_counters="1"/>
                <field name="state" string="State" select="one" expand="1"/>
            </searchpanel>
        </search>
        """

        # Malformed XML arch
        self.malformed_arch = """
        <search>
            <field name="name" string="Name"
            <filter name="active" string="Active" domain="[('active', '=', True)]"/>
        </search>
        """

        # Empty arch
        self.empty_arch = "<search></search>"

    def test_simple_search_view_parsing(self):
        """Parse simple search view successfully"""
        parser = SearchViewParser(self.simple_arch)
        result = parser.parse()

        self.assertIn("fields", result)
        self.assertIn("filters", result)
        self.assertIn("groups", result)
        self.assertIn("separators", result)
        self.assertIn("search_panel", result)

        # Check fields
        self.assertEqual(len(result["fields"]), 2)
        self.assertEqual(result["fields"][0]["name"], "name")
        self.assertEqual(result["fields"][0]["string"], "Name")
        self.assertEqual(result["fields"][1]["name"], "date")

        # Check filters
        self.assertEqual(len(result["filters"]), 1)
        self.assertEqual(result["filters"][0]["name"], "active")
        self.assertEqual(result["filters"][0]["domain"], "[('active', '=', True)]")

    def test_complex_search_view_parsing(self):
        """Parse complex search view with all elements"""
        parser = SearchViewParser(self.complex_arch)
        result = parser.parse()

        # Verify fields with attributes (all)
        fields = result["fields"]
        self.assertEqual(len(fields), 5)

        name_field = next(f for f in fields if f["name"] == "name")
        self.assertEqual(name_field["filter_domain"], "[('name', 'ilike', self)]")

        partner_field = next(f for f in fields if f["name"] == "partner_id")
        self.assertEqual(partner_field["operator"], "child_of")

        date_field = next(f for f in fields if f["name"] == "date")
        self.assertEqual(date_field["context"], "{'default_date': self}")

        # Verify filters (all)
        filters = result["filters"]
        self.assertEqual(len(filters), 6)

        # Check specific filter attributes
        inactive_filter = next(f for f in filters if f["name"] == "inactive")
        self.assertEqual(inactive_filter["help"], "Show inactive records")

        date_filter = next(f for f in filters if f["name"] == "date_filter")
        self.assertEqual(date_filter["date"], "date")
        self.assertEqual(date_filter["default_period"], "this_month")

        # Verify groups
        groups = result["groups"]
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["expand"], "0")
        self.assertEqual(groups[0]["string"], "Group By")
        self.assertEqual(len(groups[0]["filters"]), 2)

        # Verify separators
        separators = result["separators"]
        self.assertEqual(len(separators), 2)
        self.assertEqual(separators[0]["string"], "Filters")

        # Verify search panel
        search_panel = result["search_panel"]
        self.assertEqual(len(search_panel["fields"]), 2)

        category_field = next(
            f for f in search_panel["fields"] if f["name"] == "category_id"
        )
        self.assertEqual(category_field["select"], "multi")
        self.assertEqual(category_field["enable_counters"], "1")

    def test_empty_search_view_parsing(self):
        """Parse empty search view"""
        parser = SearchViewParser(self.empty_arch)
        result = parser.parse()

        self.assertEqual(len(result["fields"]), 0)
        self.assertEqual(len(result["filters"]), 0)
        self.assertEqual(len(result["groups"]), 0)
        self.assertEqual(len(result["separators"]), 0)
        self.assertEqual(result["search_panel"], {})

    def test_malformed_xml_handling(self):
        """Handle malformed XML gracefully"""
        with self.assertRaises(etree.XMLSyntaxError):
            SearchViewParser(self.malformed_arch)

    def test_invalid_xml_structure_handling(self):
        """Handle invalid XML structure"""
        invalid_arch = "<invalid><field name='test'/></invalid>"
        with self.assertRaises(ValueError):
            SearchViewParser(invalid_arch)

    def test_none_attributes_filtering(self):
        """Verify None attributes are filtered out"""
        arch_with_empty_attrs = """
        <search>
            <field name="test" string="Test"/>
            <filter name="test_filter" string="Filter"/>
        </search>
        """
        parser = SearchViewParser(arch_with_empty_attrs)
        result = parser.parse()

        # Check that only non-None attributes are present
        field = result["fields"][0]
        self.assertNotIn("filter_domain", field)
        self.assertNotIn("operator", field)

        filter_item = result["filters"][0]
        self.assertNotIn("domain", filter_item)
        self.assertNotIn("help", filter_item)

    def test_nested_group_filters_parsing(self):
        """Test parsing of filters within groups"""
        arch_with_nested = """
        <search>
            <group string="Advanced">
                <filter name="group1" string="Group 1" context="{'group_by': 'field1'}"/>
                <filter name="group2" string="Group 2" context="{'group_by': 'field2'}" domain="[('active', '=', True)]"/>
            </group>
        </search>
        """
        parser = SearchViewParser(arch_with_nested)
        result = parser.parse()

        self.assertEqual(len(result["groups"]), 1)
        group = result["groups"][0]
        self.assertEqual(len(group["filters"]), 2)

        filter1 = group["filters"][0]
        self.assertEqual(filter1["name"], "group1")
        self.assertEqual(filter1["context"], "{'group_by': 'field1'}")

        filter2 = group["filters"][1]
        self.assertEqual(filter2["domain"], "[('active', '=', True)]")

    def test_multiple_search_panels(self):
        """Test handling of multiple search panel fields"""
        arch_multiple_panels = """
        <search>
            <searchpanel>
                <field name="field1" select="one" icon="fa-user"/>
                <field name="field2" select="multi" color="blue"/>
                <field name="field3" expand="1" domain="[('active', '=', True)]"/>
            </searchpanel>
        </search>
        """
        parser = SearchViewParser(arch_multiple_panels)
        result = parser.parse()

        panel_fields = result["search_panel"]["fields"]
        self.assertEqual(len(panel_fields), 3)

        field1 = next(f for f in panel_fields if f["name"] == "field1")
        self.assertEqual(field1["icon"], "fa-user")

        field2 = next(f for f in panel_fields if f["name"] == "field2")
        self.assertEqual(field2["color"], "blue")

        field3 = next(f for f in panel_fields if f["name"] == "field3")
        self.assertEqual(field3["domain"], "[('active', '=', True)]")

    def test_unicode_content_handling(self):
        """Test handling of unicode content in arch"""
        unicode_arch = """
        <search>
            <field name="name" string="Nombre"/>
            <filter name="active" string="Activo" domain="[('active', '=', True)]"/>
            <separator string="Filtros Avanzados"/>
        </search>
        """
        parser = SearchViewParser(unicode_arch)
        result = parser.parse()

        self.assertEqual(result["fields"][0]["string"], "Nombre")
        self.assertEqual(result["filters"][0]["string"], "Activo")
        self.assertEqual(result["separators"][0]["string"], "Filtros Avanzados")

    def test_large_xml_performance(self):
        """Test performance with large XML structures"""
        # Create large arch with many elements
        large_fields = "".join(
            [f'<field name="field_{i}" string="Field {i}"/>' for i in range(100)]
        )
        large_filters = "".join(
            [
                f'<filter name="filter_{i}" string="Filter {i}" domain="[(\'field_{i}\', \'=\', True)]"/>'
                for i in range(100)
            ]
        )

        large_arch = f"<search>{large_fields}{large_filters}</search>"

        start_time = time.time()
        parser = SearchViewParser(large_arch)
        result = parser.parse()
        end_time = time.time()

        # Parsing should complete within reasonable time (< 1 second)
        self.assertLess(end_time - start_time, 1.0)

        # Verify all elements were parsed
        self.assertEqual(len(result["fields"]), 100)
        self.assertEqual(len(result["filters"]), 100)

    def test_memory_usage_with_repeated_parsing(self):
        """Test memory efficiency with repeated parsing operations"""
        import gc

        # Parse the same arch multiple times
        for _i in range(50):
            parser = SearchViewParser(self.complex_arch)
            result = parser.parse()

            # Verify parsing still works correctly
            self.assertIn("fields", result)
            self.assertGreater(len(result["fields"]), 0)

        # Force garbage collection
        gc.collect()

        # Should complete without memory errors
        self.assertTrue(True)

    def test_xpath_injection_security(self):
        """Test security against XPath injection"""
        malicious_arch = """
        <search>
            <field name="name[1=1 or 1=1]" string="Test"/>
            <filter name="test" domain="[('field', '=', 'value')]"/>
        </search>
        """

        parser = SearchViewParser(malicious_arch)
        result = parser.parse()

        # Should parse normally, treating the malicious content as regular attribute value
        self.assertEqual(len(result["fields"]), 1)
        self.assertEqual(result["fields"][0]["name"], "name[1=1 or 1=1]")

    def test_deeply_nested_structure(self):
        """Test handling of deeply nested XML structures"""
        nested_arch = """
        <search>
            <group string="Level 1">
                <group string="Level 2">
                    <filter name="nested" string="Nested Filter" context="{'test': True}"/>
                </group>
            </group>
        </search>
        """

        parser = SearchViewParser(nested_arch)
        result = parser.parse()

        # Should find nested elements correctly
        self.assertEqual(len(result["groups"]), 2)

    def test_special_characters_in_attributes(self):
        """Test handling of special characters in XML attributes"""
        special_arch = """
        <search>
            <field name="field_with_&amp;_char" string="Test &amp; Field"/>
            <filter name="special" string="Filter &lt;&gt;" domain="[('field', '=', '&quot;value&quot;')]"/>
        </search>
        """

        parser = SearchViewParser(special_arch)
        result = parser.parse()

        self.assertEqual(result["fields"][0]["name"], "field_with_&_char")
        self.assertEqual(result["fields"][0]["string"], "Test & Field")
        self.assertEqual(
            result["filters"][0]["domain"], "[('field', '=', '\"value\"')]"
        )

    def test_parser_instance_reusability(self):
        """Test that parser instance can be reused safely"""
        parser = SearchViewParser(self.simple_arch)

        # Parse multiple times with same instance
        result1 = parser.parse()
        result2 = parser.parse()

        # Results should be identical
        self.assertEqual(result1, result2)

        # Verify data integrity
        self.assertEqual(len(result1["fields"]), 2)
        self.assertEqual(len(result2["fields"]), 2)

    def test_concurrent_parsing_safety(self):
        """Test thread safety of parsing operations"""
        import threading

        results = []
        errors = []

        def parse_arch():
            """Thread worker function to parse search view architecture."""
            try:
                parser = SearchViewParser(self.complex_arch)
                result = parser.parse()
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = []
        for _i in range(10):
            thread = threading.Thread(target=parse_arch)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify no errors occurred
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(results), 10)

        # All results should be identical
        first_result = results[0]
        for result in results[1:]:
            self.assertEqual(result, first_result)

    def test_empty_string_arch_handling(self):
        """Test handling of empty string arch"""
        with self.assertRaises(etree.XMLSyntaxError):
            SearchViewParser("")

    def test_none_arch_handling(self):
        """Test handling of None arch"""
        with self.assertRaises(AttributeError):
            SearchViewParser(None)  # type: ignore

    def test_non_string_arch_handling(self):
        """Test handling of non-string arch"""
        with self.assertRaises(AttributeError):
            SearchViewParser(123)  # type: ignore

    def test_missing_search_root_element(self):
        """Test arch without search root element"""
        arch_no_search = "<form><field name='test'/></form>"
        with self.assertRaises(ValueError):
            SearchViewParser(arch_no_search)

    def test_field_with_all_attributes(self):
        """Test field with all possible attributes"""
        arch_full_field = """
        <search>
            <field name="complex_field"
                   string="Complex Field"
                   filter_domain="[('name', 'ilike', self)]"
                   operator="child_of"
                   domain="[('active', '=', True)]"
                   context="{'default_value': 'test'}"/>
        </search>
        """
        parser = SearchViewParser(arch_full_field)
        result = parser.parse()

        field = result["fields"][0]
        self.assertEqual(field["name"], "complex_field")
        self.assertEqual(field["string"], "Complex Field")
        self.assertEqual(field["filter_domain"], "[('name', 'ilike', self)]")
        self.assertEqual(field["operator"], "child_of")
        self.assertEqual(field["domain"], "[('active', '=', True)]")
        self.assertEqual(field["context"], "{'default_value': 'test'}")

    def test_filter_with_all_attributes(self):
        """Test filter with all possible attributes"""
        arch_full_filter = """
        <search>
            <filter name="complex_filter"
                    string="Complex Filter"
                    domain="[('active', '=', True)]"
                    context="{'group_by': 'partner_id'}"
                    help="This is a help text"
                    invisible="1"
                    date="create_date"
                    default_period="last_month"/>
        </search>
        """
        parser = SearchViewParser(arch_full_filter)
        result = parser.parse()

        filter_item = result["filters"][0]
        self.assertEqual(filter_item["name"], "complex_filter")
        self.assertEqual(filter_item["string"], "Complex Filter")
        self.assertEqual(filter_item["domain"], "[('active', '=', True)]")
        self.assertEqual(filter_item["context"], "{'group_by': 'partner_id'}")
        self.assertEqual(filter_item["help"], "This is a help text")
        self.assertEqual(filter_item["invisible"], "1")
        self.assertEqual(filter_item["date"], "create_date")
        self.assertEqual(filter_item["default_period"], "last_month")

    def test_search_panel_with_all_attributes(self):
        """Test search panel field with all possible attributes"""
        arch_full_panel = """
        <search>
            <searchpanel>
                <field name="panel_field"
                       string="Panel Field"
                       select="multi"
                       icon="fa-star"
                       color="red"
                       enable_counters="1"
                       expand="0"
                       domain="[('visible', '=', True)]"/>
            </searchpanel>
        </search>
        """
        parser = SearchViewParser(arch_full_panel)
        result = parser.parse()

        panel_field = result["search_panel"]["fields"][0]
        self.assertEqual(panel_field["name"], "panel_field")
        self.assertEqual(panel_field["string"], "Panel Field")
        self.assertEqual(panel_field["select"], "multi")
        self.assertEqual(panel_field["icon"], "fa-star")
        self.assertEqual(panel_field["color"], "red")
        self.assertEqual(panel_field["enable_counters"], "1")
        self.assertEqual(panel_field["expand"], "0")
        self.assertEqual(panel_field["domain"], "[('visible', '=', True)]")

    def test_very_large_xml_stress_test(self):
        """Stress test with very large XML (performance and memory)"""
        # Create extremely large arch (1000 elements)
        large_elements = "".join(
            [
                f'<field name="field_{i}" string="Field {i}"/>'
                f'<filter name="filter_{i}" string="Filter {i}" domain="[(\'field_{i}\', \'=\', True)]"/>'
                f'<separator string="Separator {i}"/>'
                for i in range(1000)
            ]
        )

        stress_arch = f"<search>{large_elements}</search>"

        start_time = time.time()
        parser = SearchViewParser(stress_arch)
        result = parser.parse()
        end_time = time.time()

        # Should still complete in reasonable time (< 2 seconds for 1000 elements)
        self.assertLess(end_time - start_time, 2.0)

        # Verify correct parsing
        self.assertEqual(len(result["fields"]), 1000)
        self.assertEqual(len(result["filters"]), 1000)
        self.assertEqual(len(result["separators"]), 1000)

    def test_xml_with_comments_and_cdata(self):
        """Test XML with comments and CDATA sections"""
        arch_with_comments = """
        <search>
            <!-- This is a comment -->
            <field name="name" string="Name"/>
            <!-- Another comment -->
            <filter name="active" string="Active"
                    domain="[('active', '=', True)]">
                <![CDATA[This is CDATA content]]>
            </filter>
        </search>
        """
        parser = SearchViewParser(arch_with_comments)
        result = parser.parse()

        # Should parse normally, ignoring comments and CDATA
        self.assertEqual(len(result["fields"]), 1)
        self.assertEqual(len(result["filters"]), 1)
        self.assertEqual(result["fields"][0]["name"], "name")

    def test_arch_with_namespaces(self):
        """Test XML with namespaces"""
        namespaced_arch = """
        <odoo:search xmlns:odoo="http://odoo.com">
            <odoo:field name="name" string="Name"/>
            <odoo:filter name="active" string="Active" domain="[('active', '=', True)]"/>
        </odoo:search>
        """
        # This should raise ValueError since we expect 'search' root (not 'odoo:search')
        with self.assertRaises(ValueError):
            SearchViewParser(namespaced_arch)

    def test_invalid_encoding_handling(self):
        """Test handling of invalid encoding"""
        # Create arch with special characters
        special_char_arch = """
        <search>
            <field name="test_éñü" string="Test éñü"/>
            <filter name="active" string="Activo ñ" domain="[('active', '=', True)]"/>
        </search>
        """
        parser = SearchViewParser(special_char_arch)
        result = parser.parse()

        self.assertEqual(result["fields"][0]["name"], "test_éñü")
        self.assertEqual(result["fields"][0]["string"], "Test éñü")
        self.assertEqual(result["filters"][0]["string"], "Activo ñ")

    def test_extremely_nested_groups(self):
        """Test handling of extremely nested group structures"""
        nested_groups = """
        <search>
            <group string="Level 1">
                <group string="Level 2">
                    <group string="Level 3">
                        <group string="Level 4">
                            <filter name="deep_filter" string="Deep Filter" context="{'group_by': 'field'}"/>
                        </group>
                    </group>
                </group>
            </group>
        </search>
        """
        parser = SearchViewParser(nested_groups)
        result = parser.parse()

        # Should find all nested groups
        self.assertEqual(len(result["groups"]), 4)

        # Verify deep filter is found
        deep_group = result["groups"][3]  # Deepest group
        self.assertEqual(len(deep_group["filters"]), 1)
        self.assertEqual(deep_group["filters"][0]["name"], "deep_filter")

    def test_duplicate_element_names(self):
        """Test handling of duplicate element names"""
        duplicate_arch = """
        <search>
            <field name="name" string="Name 1"/>
            <field name="name" string="Name 2"/>
            <filter name="active" string="Active 1" domain="[('active', '=', True)]"/>
            <filter name="active" string="Active 2" domain="[('active', '=', False)]"/>
        </search>
        """
        parser = SearchViewParser(duplicate_arch)
        result = parser.parse()

        # Should include all elements, even with duplicate names
        self.assertEqual(len(result["fields"]), 2)
        self.assertEqual(len(result["filters"]), 2)

        # Verify both versions are preserved
        names = [f["string"] for f in result["fields"]]
        self.assertIn("Name 1", names)
        self.assertIn("Name 2", names)

    def test_parser_memory_cleanup(self):
        """Test that parser properly cleans up memory"""
        import weakref

        parser = SearchViewParser(self.simple_arch)
        parser.parse()

        # Create weak reference to parser
        parser_ref = weakref.ref(parser)

        # Delete parser
        del parser

        # Force garbage collection
        import gc

        gc.collect()

        # Parser should be garbage collected
        # Note: This might not always pass immediately due to Python's GC behavior
        # But it's good to test memory cleanup patterns
        self.assertIsNone(parser_ref())

    def test_include_fields_on_search_panel_false(self):
        """Test that fields inside searchpanel are included when include_fields_on_search_panel is False"""
        arch_with_panel_fields = """
        <search>
            <field name="name" string="Name"/>
            <field name="date" string="Date"/>
            <searchpanel>
                <field name="category_id" string="Category" select="multi"/>
                <field name="state" string="State" select="one"/>
            </searchpanel>
        </search>
        """
        parser = SearchViewParser(arch_with_panel_fields)
        result = parser.parse(include_fields_on_search_panel=False)

        # Should include all fields (including those in searchpanel)
        self.assertEqual(len(result["fields"]), 4)
        field_names = [f["name"] for f in result["fields"]]
        self.assertIn("name", field_names)
        self.assertIn("date", field_names)
        self.assertIn("category_id", field_names)
        self.assertIn("state", field_names)

    def test_include_fields_on_search_panel_true(self):
        """Test that fields inside searchpanel are excluded when include_fields_on_search_panel is True"""
        arch_with_panel_fields = """
        <search>
            <field name="name" string="Name"/>
            <field name="date" string="Date"/>
            <searchpanel>
                <field name="category_id" string="Category" select="multi"/>
                <field name="state" string="State" select="one"/>
            </searchpanel>
        </search>
        """
        parser = SearchViewParser(arch_with_panel_fields)
        result = parser.parse(include_fields_on_search_panel=True)

        # Should exclude fields inside searchpanel
        self.assertEqual(len(result["fields"]), 2)
        field_names = [f["name"] for f in result["fields"]]
        self.assertIn("name", field_names)
        self.assertIn("date", field_names)
        self.assertNotIn("category_id", field_names)
        self.assertNotIn("state", field_names)

        # But search panel should still have its fields
        self.assertEqual(len(result["search_panel"]["fields"]), 2)

    def test_include_fields_on_search_panel_default_behavior(self):
        """Test default behavior when include_fields_on_search_panel is not specified"""
        arch_with_panel_fields = """
        <search>
            <field name="name" string="Name"/>
            <searchpanel>
                <field name="category_id" string="Category" select="multi"/>
            </searchpanel>
        </search>
        """
        parser = SearchViewParser(arch_with_panel_fields)
        result = parser.parse()  # No parameter specified

        # Should include all fields by default (include_fields_on_search_panel defaults to False)
        self.assertEqual(len(result["fields"]), 2)
        field_names = [f["name"] for f in result["fields"]]
        self.assertIn("name", field_names)
        self.assertIn("category_id", field_names)

    def test_nested_searchpanel_fields_exclusion(self):
        """Test exclusion of deeply nested fields within searchpanel"""
        arch_nested_panel = """
        <search>
            <field name="top_level" string="Top Level"/>
            <searchpanel>
                <group>
                    <field name="nested_field" string="Nested Field"/>
                </group>
                <field name="direct_field" string="Direct Field"/>
            </searchpanel>
        </search>
        """
        parser = SearchViewParser(arch_nested_panel)
        result = parser.parse(include_fields_on_search_panel=True)

        # Should only include top-level field
        self.assertEqual(len(result["fields"]), 1)
        self.assertEqual(result["fields"][0]["name"], "top_level")

    def test_multiple_searchpanel_sections_exclusion(self):
        """Test exclusion when there are multiple searchpanel sections"""
        arch_multiple_panels = """
        <search>
            <field name="main_field" string="Main Field"/>
            <searchpanel>
                <field name="panel1_field" string="Panel 1 Field"/>
            </searchpanel>
            <field name="middle_field" string="Middle Field"/>
            <searchpanel>
                <field name="panel2_field" string="Panel 2 Field"/>
            </searchpanel>
        </search>
        """
        parser = SearchViewParser(arch_multiple_panels)
        result = parser.parse(include_fields_on_search_panel=True)

        # Should exclude all fields inside any searchpanel
        self.assertEqual(len(result["fields"]), 2)
        field_names = [f["name"] for f in result["fields"]]
        self.assertIn("main_field", field_names)
        self.assertIn("middle_field", field_names)
        self.assertNotIn("panel1_field", field_names)
        self.assertNotIn("panel2_field", field_names)

    def test_include_first_level_filters_only_false(self):
        """Test that nested filters are included when include_first_level_filters_only is False"""
        arch_with_nested_filters = """
        <search>
            <filter name="top_level_filter" string="Top Level" domain="[('active', '=', True)]"/>
            <group string="Group Filters">
                <filter name="group_filter1" string="Group Filter 1" context="{'group_by': 'partner_id'}"/>
                <filter name="group_filter2" string="Group Filter 2" context="{'group_by': 'date'}"/>
            </group>
            <filter name="another_top_filter" string="Another Top" domain="[('visible', '=', True)]"/>
        </search>
        """
        parser = SearchViewParser(arch_with_nested_filters)
        result = parser.parse(include_first_level_filters_only=False)

        # Should include all filters (top level and nested)
        self.assertEqual(len(result["filters"]), 4)
        filter_names = [f["name"] for f in result["filters"]]
        self.assertIn("top_level_filter", filter_names)
        self.assertIn("group_filter1", filter_names)
        self.assertIn("group_filter2", filter_names)
        self.assertIn("another_top_filter", filter_names)

    def test_include_first_level_filters_only_true(self):
        """Test that only direct child filters are included when include_first_level_filters_only is True"""
        arch_with_nested_filters = """
        <search>
            <filter name="top_level_filter" string="Top Level" domain="[('active', '=', True)]"/>
            <group string="Group Filters">
                <filter name="group_filter1" string="Group Filter 1" context="{'group_by': 'partner_id'}"/>
                <filter name="group_filter2" string="Group Filter 2" context="{'group_by': 'date'}"/>
            </group>
            <filter name="another_top_filter" string="Another Top" domain="[('visible', '=', True)]"/>
        </search>
        """
        parser = SearchViewParser(arch_with_nested_filters)
        result = parser.parse(include_first_level_filters_only=True)

        # Should only include direct child filters
        self.assertEqual(len(result["filters"]), 2)
        filter_names = [f["name"] for f in result["filters"]]
        self.assertIn("top_level_filter", filter_names)
        self.assertIn("another_top_filter", filter_names)
        self.assertNotIn("group_filter1", filter_names)
        self.assertNotIn("group_filter2", filter_names)

        # But groups should still have their filters
        self.assertEqual(len(result["groups"]), 1)
        self.assertEqual(len(result["groups"][0]["filters"]), 2)

    def test_include_first_level_filters_only_default_behavior(self):
        """Test default behavior when include_first_level_filters_only is not specified"""
        arch_with_nested_filters = """
        <search>
            <filter name="top_filter" string="Top Filter" domain="[('active', '=', True)]"/>
            <group string="Advanced">
                <filter name="nested_filter" string="Nested Filter" context="{'group_by': 'field'}"/>
            </group>
        </search>
        """
        parser = SearchViewParser(arch_with_nested_filters)
        result = parser.parse()  # No parameter specified

        # Should include all filters by default (include_first_level_filters_only defaults to False)
        self.assertEqual(len(result["filters"]), 2)
        filter_names = [f["name"] for f in result["filters"]]
        self.assertIn("top_filter", filter_names)
        self.assertIn("nested_filter", filter_names)

    def test_deeply_nested_filters_exclusion(self):
        """Test exclusion of deeply nested filters"""
        arch_deeply_nested = """
        <search>
            <filter name="level1_filter" string="Level 1" domain="[('active', '=', True)]"/>
            <group string="Level 1 Group">
                <group string="Level 2 Group">
                    <filter name="level3_filter" string="Level 3" context="{'group_by': 'field'}"/>
                </group>
                <filter name="level2_filter" string="Level 2" context="{'group_by': 'partner'}"/>
            </group>
        </search>
        """
        parser = SearchViewParser(arch_deeply_nested)
        result = parser.parse(include_first_level_filters_only=True)

        # Should only include level 1 filter
        self.assertEqual(len(result["filters"]), 1)
        self.assertEqual(result["filters"][0]["name"], "level1_filter")

    def test_no_direct_child_filters(self):
        """Test when there are no direct child filters, only nested ones"""
        arch_no_direct_filters = """
        <search>
            <field name="name" string="Name"/>
            <group string="All Filters Here">
                <filter name="nested_filter1" string="Nested 1" domain="[('active', '=', True)]"/>
                <filter name="nested_filter2" string="Nested 2" domain="[('visible', '=', True)]"/>
            </group>
        </search>
        """
        parser = SearchViewParser(arch_no_direct_filters)
        result = parser.parse(include_first_level_filters_only=True)

        # Should return empty filters list
        self.assertEqual(len(result["filters"]), 0)

        # But groups should still work
        self.assertEqual(len(result["groups"]), 1)
        self.assertEqual(len(result["groups"][0]["filters"]), 2)

    def test_mixed_elements_with_first_level_only(self):
        """Test mixed elements (separators, fields) don't interfere with first-level filter logic"""
        arch_mixed = """
        <search>
            <field name="name" string="Name"/>
            <filter name="direct_filter" string="Direct" domain="[('active', '=', True)]"/>
            <separator string="Advanced Options"/>
            <group string="Grouped">
                <filter name="grouped_filter" string="Grouped" context="{'group_by': 'date'}"/>
                <separator string="Group Separator"/>
            </group>
            <filter name="another_direct" string="Another Direct" domain="[('visible', '=', True)]"/>
        </search>
        """
        parser = SearchViewParser(arch_mixed)
        result = parser.parse(include_first_level_filters_only=True)

        # Should only get direct filters
        self.assertEqual(len(result["filters"]), 2)
        filter_names = [f["name"] for f in result["filters"]]
        self.assertIn("direct_filter", filter_names)
        self.assertIn("another_direct", filter_names)
        self.assertNotIn("grouped_filter", filter_names)

        # Other elements should be unaffected
        self.assertEqual(len(result["fields"]), 1)
        self.assertEqual(
            len(result["separators"]), 2
        )  # Both separators should be found
        self.assertEqual(len(result["groups"]), 1)

    def test_valid_search_element_as_root(self):
        """Test that search element as root is valid"""
        arch = """
        <search>
            <field name="name" string="Name"/>
            <filter name="active" string="Active" domain="[('active', '=', True)]"/>
        </search>
        """
        # Should not raise any exception
        parser = SearchViewParser(arch)
        result = parser.parse()
        self.assertEqual(len(result["fields"]), 1)
        self.assertEqual(len(result["filters"]), 1)

    def test_search_element_as_child_raises_error(self):
        """Test that search element as child of root raises ValueError"""
        arch = """
        <root>
            <search>
                <field name="name" string="Name"/>
                <filter name="active" string="Active" domain="[('active', '=', True)]"/>
            </search>
        </root>
        """
        # Should raise ValueError since search is not root
        with self.assertRaises(ValueError) as context:
            SearchViewParser(arch)

        self.assertIn("El elemento raíz debe ser 'search'", str(context.exception))

    def test_no_search_element_raises_error(self):
        """Test that absence of search element raises ValueError"""
        arch = """
        <form>
            <field name="name" string="Name"/>
            <button name="action" string="Action"/>
        </form>
        """
        with self.assertRaises(ValueError) as context:
            SearchViewParser(arch)

        self.assertIn(
            "El elemento raíz debe ser 'search', encontrado", str(context.exception)
        )

    def test_empty_root_raises_error(self):
        """Test that XML without search raises ValueError"""
        arch = """
        <root>
            <field name="name" string="Name"/>
            <filter name="active" string="Active"/>
        </root>
        """
        with self.assertRaises(ValueError) as context:
            SearchViewParser(arch)

        self.assertIn(
            "El elemento raíz debe ser 'search', encontrado:", str(context.exception)
        )

    def test_nested_search_not_found(self):
        """Test that deeply nested search elements are not found (only direct children)"""
        arch = """
        <root>
            <wrapper>
                <search>
                    <field name="name" string="Name"/>
                </search>
            </wrapper>
        </root>
        """
        with self.assertRaises(ValueError) as context:
            SearchViewParser(arch)

        self.assertIn("El elemento raíz debe ser 'search'", str(context.exception))

    def test_nested_search_raises_error(self):
        """Test that search element nested within other elements raises ValueError"""
        arch = """
        <root>
            <!-- These elements should NOT be found -->
            <field name="outside_field" string="Outside Field"/>
            <filter name="outside_filter" string="Outside Filter"/>

            <search>
                <!-- These elements would be found if search was root -->
                <field name="inside_field" string="Inside Field"/>
                <filter name="inside_filter" string="Inside Filter"/>
            </search>
        </root>
        """
        # Should raise ValueError since search is not root
        with self.assertRaises(ValueError) as context:
            SearchViewParser(arch)

        self.assertIn("El elemento raíz debe ser 'search'", str(context.exception))

    def test_first_level_filters_only_with_search_root(self):
        """Test that first level filter restriction works with search as root"""
        arch = """
        <search>
            <filter name="direct_filter" string="Direct"/>
            <group string="Group">
                <filter name="nested_filter" string="Nested"/>
            </group>
        </search>
        """
        parser = SearchViewParser(arch)
        result = parser.parse(include_first_level_filters_only=True)

        # Should only find direct_filter (not nested_filter)
        self.assertEqual(len(result["filters"]), 1)
        self.assertEqual(result["filters"][0]["name"], "direct_filter")

    def test_search_panel_fields_exclusion_with_search_root(self):
        """Test that search panel exclusion works with search as root"""
        arch = """
        <search>
            <field name="main_field" string="Main Field"/>
            <searchpanel>
                <field name="panel_field" string="Panel Field"/>
            </searchpanel>
        </search>
        """
        parser = SearchViewParser(arch)
        result = parser.parse(include_fields_on_search_panel=True)

        # Should only find main_field (excluding panel fields)
        self.assertEqual(len(result["fields"]), 1)
        self.assertEqual(result["fields"][0]["name"], "main_field")

        # But search panel should work correctly
        self.assertEqual(len(result["search_panel"]["fields"]), 1)
        self.assertEqual(result["search_panel"]["fields"][0]["name"], "panel_field")
