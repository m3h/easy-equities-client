from dataclasses import dataclass
from datetime import date
from typing import List, Optional

from bs4 import BeautifulSoup
from bs4.element import Tag

from easy_equities_client.accounts.types import Account, Holding


def extract_account_info(account_div: Tag) -> Optional[Account]:
    trading_currency = account_div.parent.attrs.get("data-tradingcurrencyid")
    if not trading_currency:
        return None
    return Account(
        name=account_div.text.strip(),
        trading_currency_id=trading_currency.strip(),
        id=account_div.parent.attrs["data-id"].strip(),
    )


@dataclass
class AccountOverviewParser:
    """
    Parse the accounts overview page (/AccountOverview) given the html
    contents of the page.
    """

    page: str

    def extract_accounts(self) -> List[Account]:
        """
        Return the accounts found on the account overview page.
        """
        soup = BeautifulSoup(self.page, "html.parser")
        accounts_divs = soup.find_all(attrs={"id": "trust-account-types"})
        return [
            account
            for account in [
                extract_account_info(account_div) for account_div in accounts_divs
            ]
            if account
        ]


class HoldingFieldNotFoundException(Exception):
    def __init__(self, field, exception):
        return super().__init__(
            f"Field '{field}' not found in holding div. Exception: f{exception}"
        )


class HoldingDivParser:
    def __init__(self, div: Tag):
        self.div = div

    def __eq__(a, b):
        return a.name == b.name

    def __hash__(self):
        return hash(self.name)

    @property
    def name(self) -> str:
        return self.div.find(attrs={'class': 'equity-image-as-text'}).text.strip()

    @property
    def purchase_value(self) -> str:
        return self.div.find(attrs={'class': 'purchase-value-cell'}).text.strip()

    @property
    def current_value(self) -> str:
        return self.div.find(attrs={'class': 'current-value-cell'}).text.strip()

    @property
    def current_price(self) -> str:
        return self.div.find(attrs={'class': 'current-price-cell'}).text.strip()

    @property
    def img(self) -> str:
        return self.div.find(attrs={'class': 'instrument'}).attrs['src']

    @property
    def contract_code(self) -> str:
        return self.img[self.img.rindex('/') + 1 : self.img.index('.png')]

    @property
    def view_url(self) -> str:
        return (
            self.div.find(attrs={'class': 'collapse-container'})
            .find('span')
            .attrs['data-detailviewurl']
        )

    @property
    def isin(self) -> str:
        return (
            self.div.find(attrs={'class': 'collapse-container'})
            .find('span')
            .attrs['data-detailviewurl']
            .split('=')[-1]
        )

    def to_dict(self) -> Holding:
        fields = [
            'name',
            'contract_code',
            'purchase_value',
            'current_value',
            'current_price',
            'img',
            'view_url',
            'isin',
        ]
        data: Holding = {}
        for field in fields:
            try:
                data[field] = getattr(self, field)  # type: ignore
            except Exception as e:
                raise HoldingFieldNotFoundException(field, e)

        return data


@dataclass
class AccountHoldingsParser:
    """
    Parse the accounts holdings page given the html contents of the page.
    """

    page: bytes

    def extract_holdings(self) -> List[Holding]:
        """
        Return the holdings found on the holdings page.
        """
        soup = BeautifulSoup(self.page, "html.parser")
        holdings_divs = soup.find_all(attrs={'class': 'holding-inner-container'})
        divs = set([HoldingDivParser(holding_div) for holding_div in holdings_divs[1:] if 'holding-table-header' not in holding_div.parent.attrs['class']])
        return [div.to_dict() for div in divs]

@dataclass
class TransactionHistorySearchParser:
    """
    Parse the Transaction History Search page given the html contents of the page.
    """

    page: bytes

    def extract_transaction_history(self):
        """
        Return the holdings found on the holdings page.
        """
        soup = BeautifulSoup(self.page, "html.parser")

        htmltable = soup.find('table', { 'class' : 'table table-style' })
        rows = list()
        for row in htmltable.tbody.findAll('tr'):
            row_data = dict()
            for column in row.findAll('td'):
                row_data[column['data-title']] = column.text.strip()
            
            row_data['DATE'] = date.fromisoformat(row_data['DATE'])

            amount_str = row_data['DEBIT/CREDIT']
            if '-' in amount_str:
                multiplier = -1
                amount_str =  amount_str.replace('-', '')
            else:
                multiplier = 1
            
            amount_str = amount_str.replace(' ', '')

            currency, amount_digits = amount_str[0], float(amount_str[1:])

            row_data['CURRENCY'] = currency
            row_data['AMOUNT'] = multiplier * amount_digits


            rows.append(row_data)

        return rows
