#!/usr/bin/env python3
"""
Test Connection Documentation for Apache Airflow

This script serves as documentation for how to test connections in Apache Airflow.
"""

def test_connection_documentation():
    """
    Documentation of how to test a connection in Airflow.
    
    This function explains the test_connection functionality that was added
    in Airflow to allow users to verify their connection settings.
    """
    print("Testing Airflow Connection Functionality")
    print("=" * 50)
    
    print("Example: Create a connection object in Airflow")
    print("# Note: In a real scenario, you would get this from the database or environment")
    print("test_conn = Connection(")
    print("    conn_id=\"test_conn\",")
    print("    conn_type=\"http\",  # Using HTTP as an example")
    print("    host=\"httpbin.org\",  # A test HTTP service")
    print("    port=80,")
    print("    extra='{\"verify\": \"false\"}'  # Disable SSL verification for testing")
    print(")")
    
    print("\n# Test the connection using the built-in test_connection method")
    print("# This will call the appropriate hook's test_connection method")
    print("status, message = test_conn.test_connection()")
    print("\nTo use the test connection API endpoint, you need to enable it in config:")
    print("1. Via environment variable: AIRFLOW__CORE__TEST_CONNECTION=Enabled")
    print("2. Or in airflow.cfg: [core] test_connection = Enabled")
    
    print("\nThen you can use:")
    print("- Airflow UI: Connection form will have a 'Test Connection' button")
    print("- Airflow CLI: airflow connections test <conn_id>")
    print("- REST API: POST /api/v1/connections/test")


def test_connection_via_cli():
    """
    Shows how to test a connection using the CLI command.
    """
    print("\n" + "=" * 50)
    print("Testing Connection via CLI")
    print("=" * 50)
    
    print("To test a connection via CLI, use:")
    print("airflow connections test <connection_id>")
    print()
    print("For example:")
    print("airflow connections test postgres_default")
    print()
    print("Note: You must have test_connection enabled in your Airflow configuration.")


def enable_test_connection():
    """
    Shows how to enable test connection functionality.
    """
    print("\n" + "=" * 50)
    print("Enabling Test Connection")
    print("=" * 50)
    
    print("Option 1: Environment variable")
    print("export AIRFLOW__CORE__TEST_CONNECTION=Enabled")
    print()
    
    print("Option 2: In airflow.cfg")
    print("[core]")
    print("test_connection = Enabled")
    print()
    
    print("Valid values:")
    print("- 'Enabled': Allows testing and shows UI button")
    print("- 'Disabled': Prevents testing (default)")
    print("- 'Hidden': Prevents testing and hides UI button")
    print()
    
    print("Security Note: Only enable for trusted users with edit permissions!")


def test_connection_api_example():
    """
    Shows how to test connection via REST API.
    """
    print("\n" + "=" * 50)
    print("Testing Connection via REST API")
    print("=" * 50)
    
    print("Endpoint: POST /api/v1/connections/test")
    print("Content-Type: application/json")
    print()
    print("Request body example:")
    print("{")
    print("  \"connection_id\": \"my_test_conn\",")
    print("  \"conn_type\": \"postgres\",")
    print("  \"host\": \"localhost\",")
    print("  \"login\": \"myuser\",")
    print("  \"password\": \"mypass\",")
    print("  \"schema\": \"mydb\",")
    print("  \"port\": 5432,")
    print("  \"extra\": \"{}\"")
    print("}")
    print()
    print("Response:")
    print("{")
    print("  \"status\": true,")
    print("  \"message\": \"Connection successfully tested\"")
    print("}")


if __name__ == "__main__":
    test_connection_documentation()
    test_connection_via_cli()
    enable_test_connection()
    test_connection_api_example()