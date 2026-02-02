"""
Google Sheets Client for Taleemabad Financial Model.
OAuth2 authentication with token caching, following established patterns.
"""

import os
import pickle
from typing import Dict, List, Optional, Any
from datetime import datetime

try:
    import gspread
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False


class GoogleSheetsClient:
    """
    Google Sheets client with OAuth2 authentication.

    Follows the same authentication pattern as the fundraising app's
    Google Drive, Gmail, and Calendar clients.
    """

    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

    def __init__(
        self,
        credentials_file: str = 'config/google_credentials.json',
        token_file: str = 'config/google_sheets_token.pickle'
    ):
        """
        Initialize Google Sheets client.

        Args:
            credentials_file: Path to OAuth client credentials JSON
            token_file: Path to cached token pickle file
        """
        if not GSPREAD_AVAILABLE:
            raise ImportError(
                "Google Sheets dependencies not installed. "
                "Run: pip install gspread google-auth google-auth-oauthlib"
            )

        self.credentials_file = credentials_file
        self.token_file = token_file
        self.client: Optional[gspread.Client] = None
        self._authenticate()

    def _authenticate(self) -> None:
        """OAuth2 authentication with token caching."""
        creds = None

        # Load cached token
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)

        # Refresh expired or missing credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(
                        f"Credentials file not found: {self.credentials_file}\n"
                        "Download OAuth credentials from Google Cloud Console."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save token for future use
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)

        self.client = gspread.authorize(creds)

    def read_budget_data(
        self,
        spreadsheet_id: str,
        sheet_name: str = 'Budget'
    ) -> List[Dict[str, Any]]:
        """
        Read budget data from Google Sheet.

        Expected sheet format:
        | Category | Jan | Feb | Mar | ... | Dec |
        |----------|-----|-----|-----|-----|-----|
        | Revenue  | ... | ... | ... | ... | ... |
        | Expenses | ... | ... | ... | ... | ... |

        Args:
            spreadsheet_id: Google Sheets ID (from URL)
            sheet_name: Name of the worksheet

        Returns:
            List of dicts with budget data
        """
        try:
            spreadsheet = self.client.open_by_key(spreadsheet_id)
            worksheet = spreadsheet.worksheet(sheet_name)
            return worksheet.get_all_records()
        except gspread.SpreadsheetNotFound:
            raise ValueError(f"Spreadsheet not found: {spreadsheet_id}")
        except gspread.WorksheetNotFound:
            raise ValueError(f"Worksheet not found: {sheet_name}")

    def write_scenario_results(
        self,
        spreadsheet_id: str,
        scenario_data: Dict[str, Any],
        sheet_name: str = 'Scenarios'
    ) -> bool:
        """
        Write scenario results to Google Sheet.

        Args:
            spreadsheet_id: Google Sheets ID
            scenario_data: Dict with scenario results
            sheet_name: Name of worksheet to write to

        Returns:
            True if successful
        """
        try:
            spreadsheet = self.client.open_by_key(spreadsheet_id)

            # Get or create worksheet
            try:
                worksheet = spreadsheet.worksheet(sheet_name)
            except gspread.WorksheetNotFound:
                worksheet = spreadsheet.add_worksheet(
                    title=sheet_name,
                    rows=100,
                    cols=20
                )
                # Add headers
                headers = ['Name', 'Timestamp', 'Surplus', 'Runway', 'Revenue Mult', 'Expense Mult']
                worksheet.append_row(headers)

            # Append scenario data
            row_data = [
                scenario_data.get('name', 'Unnamed'),
                scenario_data.get('timestamp', datetime.now().isoformat()),
                scenario_data.get('surplus', 0),
                scenario_data.get('runway', 0),
                scenario_data.get('revenue_multiplier', 1.0),
                scenario_data.get('expense_multiplier', 1.0),
            ]
            worksheet.append_row(row_data)

            return True
        except Exception as e:
            print(f"Error writing to sheet: {e}")
            return False

    def get_saved_scenarios(
        self,
        spreadsheet_id: str,
        sheet_name: str = 'Scenarios'
    ) -> List[Dict[str, Any]]:
        """
        Read saved scenarios from Google Sheet.

        Args:
            spreadsheet_id: Google Sheets ID
            sheet_name: Name of scenarios worksheet

        Returns:
            List of saved scenario dicts
        """
        try:
            spreadsheet = self.client.open_by_key(spreadsheet_id)
            worksheet = spreadsheet.worksheet(sheet_name)
            records = worksheet.get_all_records()

            # Convert to scenario format
            scenarios = []
            for record in records:
                scenarios.append({
                    'name': record.get('Name', 'Unknown'),
                    'timestamp': record.get('Timestamp', ''),
                    'results': {
                        'surplus': record.get('Surplus', 0),
                        'runway': record.get('Runway', 0),
                    },
                    'revenue_multiplier': record.get('Revenue Mult', 1.0),
                    'expense_multiplier': record.get('Expense Mult', 1.0),
                })

            return scenarios
        except gspread.WorksheetNotFound:
            return []
        except Exception as e:
            print(f"Error reading scenarios: {e}")
            return []

    def sync_assumptions(
        self,
        spreadsheet_id: str,
        sheet_name: str = 'Assumptions'
    ) -> Dict[str, Any]:
        """
        Sync model assumptions from Google Sheet.

        Expected format:
        | Parameter | Value |
        |-----------|-------|
        | Opening Balance | 723248 |
        | Exchange Rate | 283 |
        | ... | ... |

        Args:
            spreadsheet_id: Google Sheets ID
            sheet_name: Name of assumptions worksheet

        Returns:
            Dict of assumptions
        """
        try:
            spreadsheet = self.client.open_by_key(spreadsheet_id)
            worksheet = spreadsheet.worksheet(sheet_name)
            records = worksheet.get_all_records()

            assumptions = {}
            key_mapping = {
                'Opening Balance': 'opening_balance',
                'Exchange Rate': 'exchange_rate',
                'Expense Multiplier': 'expense_multiplier',
            }

            for record in records:
                param = record.get('Parameter', '')
                value = record.get('Value', '')

                if param in key_mapping:
                    try:
                        assumptions[key_mapping[param]] = float(value)
                    except (ValueError, TypeError):
                        pass

            return assumptions
        except gspread.WorksheetNotFound:
            return {}
        except Exception as e:
            print(f"Error syncing assumptions: {e}")
            return {}

    def test_connection(self, spreadsheet_id: str) -> bool:
        """
        Test connection to a spreadsheet.

        Args:
            spreadsheet_id: Google Sheets ID to test

        Returns:
            True if connection successful
        """
        try:
            spreadsheet = self.client.open_by_key(spreadsheet_id)
            _ = spreadsheet.title  # Access title to verify connection
            return True
        except Exception:
            return False


def is_sheets_available() -> bool:
    """Check if Google Sheets dependencies are available."""
    return GSPREAD_AVAILABLE
