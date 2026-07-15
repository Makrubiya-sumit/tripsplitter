"""
Core business logic: turning a list of member balances into the minimum
number of payments needed to settle all debts (a classic greedy
"minimum cash flow" algorithm).
"""
from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile


def _excel_cell(reference, value, cell_type=None, style=None):
    """Return a minimal SpreadsheetML cell using inline text or numbers."""
    style_attr = f' s="{style}"' if style is not None else ''
    if cell_type == 'number':
        return f'<c r="{reference}"{style_attr}><v>{value}</v></c>'
    return f'<c r="{reference}"{style_attr} t="inlineStr"><is><t>{escape(str(value))}</t></is></c>'


def build_trip_workbook(trip, expenses):
    """Create a small, dependency-free .xlsx workbook for one trip."""
    expense_rows = list(expenses)
    rows = []
    rows.append('<row r="1">' + _excel_cell('A1', f'{trip.name} — Expense Report', style=1) + '</row>')
    rows.append('<row r="2">' + _excel_cell('A2', f'Destination: {trip.destination or "Not set"}') + '</row>')
    rows.append('<row r="3">' + _excel_cell('A3', f'Period: {trip.start_date or "Not set"} to {trip.end_date or "Not set"}') + '</row>')
    rows.append('<row r="5">' + ''.join(_excel_cell(f'{column}5', heading, style=2) for column, heading in zip('ABCDE', ['Date', 'Expense', 'Paid by', 'Notes', 'Amount (INR)'])) + '</row>')
    for index, expense in enumerate(expense_rows, start=6):
        rows.append('<row r="{0}">'.format(index) + ''.join([
            _excel_cell(f'A{index}', expense.date.isoformat()),
            _excel_cell(f'B{index}', expense.title),
            _excel_cell(f'C{index}', expense.paid_by.name),
            _excel_cell(f'D{index}', expense.notes or '—'),
            _excel_cell(f'E{index}', expense.amount, 'number', 3),
        ]) + '</row>')
    total_row = max(6, len(expense_rows) + 6)
    rows.append('<row r="{0}">'.format(total_row) + _excel_cell(f'D{total_row}', 'Total expense', style=2) + _excel_cell(f'E{total_row}', trip.total_expense, 'number', 4) + '</row>')

    summary_rows = [
        '<row r="1">' + _excel_cell('A1', f'{trip.name} — Summary', style=1) + '</row>',
        '<row r="3">' + _excel_cell('A3', 'Total expense', style=2) + _excel_cell('B3', trip.total_expense, 'number', 4) + '</row>',
        '<row r="4">' + _excel_cell('A4', 'Members', style=2) + _excel_cell('B4', trip.member_count, 'number') + '</row>',
        '<row r="5">' + _excel_cell('A5', 'Equal share per member', style=2) + _excel_cell('B5', trip.per_person_share, 'number', 4) + '</row>',
        '<row r="7">' + ''.join(_excel_cell(f'{column}7', heading, style=2) for column, heading in zip('ABC', ['Member', 'Amount paid (INR)', 'Balance (INR)'])) + '</row>',
    ]
    for index, member in enumerate(trip.members.all(), start=8):
        summary_rows.append('<row r="{0}">'.format(index) + ''.join([
            _excel_cell(f'A{index}', member.name),
            _excel_cell(f'B{index}', member.total_paid, 'number', 3),
            _excel_cell(f'C{index}', member.adjusted_balance, 'number', 3),
        ]) + '</row>')

    def sheet_xml(row_data, widths):
        return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                f'<cols>{widths}</cols><sheetData>{"".join(row_data)}</sheetData></worksheet>')

    styles = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><numFmts count="1"><numFmt numFmtId="164" formatCode="₹#,##0.00"/></numFmts><fonts count="2"><font><sz val="11"/><name val="Aptos"/></font><font><b/><sz val="11"/><name val="Aptos"/></font></fonts><fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="DCEBFF"/><bgColor indexed="64"/></patternFill></fill></fills><borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders><cellXfs count="5"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/><xf numFmtId="0" fontId="1" fillId="0" borderId="0"/><xf numFmtId="0" fontId="1" fillId="2" borderId="0"/><xf numFmtId="164" fontId="0" fillId="0" borderId="0" applyNumberFormat="1"/><xf numFmtId="164" fontId="1" fillId="2" borderId="0" applyNumberFormat="1"/></cellXfs></styleSheet>'''
    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>'''
    relationships = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'''
    workbook = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Expenses" sheetId="1" r:id="rId1"/><sheet name="Summary" sheetId="2" r:id="rId2"/></sheets></workbook>'''
    workbook_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>'''
    output = BytesIO()
    with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
        archive.writestr('[Content_Types].xml', content_types)
        archive.writestr('_rels/.rels', relationships)
        archive.writestr('xl/workbook.xml', workbook)
        archive.writestr('xl/_rels/workbook.xml.rels', workbook_rels)
        archive.writestr('xl/styles.xml', styles)
        archive.writestr('xl/worksheets/sheet1.xml', sheet_xml(rows, '<col min="1" max="1" width="14" customWidth="1"/><col min="2" max="2" width="28" customWidth="1"/><col min="3" max="3" width="20" customWidth="1"/><col min="4" max="4" width="36" customWidth="1"/><col min="5" max="5" width="16" customWidth="1"/>'))
        archive.writestr('xl/worksheets/sheet2.xml', sheet_xml(summary_rows, '<col min="1" max="1" width="28" customWidth="1"/><col min="2" max="3" width="22" customWidth="1"/>'))
    return output.getvalue()

CENT = Decimal('0.01')


def simplify_settlements(members):
    """
    Given an iterable of Member objects (each with an `adjusted_balance`
    property: positive = is owed money, negative = owes money),
    return a list of dicts: [{'from': member, 'to': member, 'amount': Decimal}, ...]
    representing the minimum set of transactions required to settle all debts.
    """
    # Build mutable (member, balance) pairs, ignoring anyone already settled.
    balances = [[m, m.adjusted_balance] for m in members if abs(m.adjusted_balance) >= CENT]

    debtors = sorted([b for b in balances if b[1] < 0], key=lambda x: x[1])           # most negative first
    creditors = sorted([b for b in balances if b[1] > 0], key=lambda x: -x[1])        # most positive first

    transactions = []
    i, j = 0, 0
    while i < len(debtors) and j < len(creditors):
        debtor, creditor = debtors[i], creditors[j]
        owe = -debtor[1]
        owed = creditor[1]
        payment = min(owe, owed).quantize(CENT)

        if payment > 0:
            transactions.append({
                'from': debtor[0],
                'to': creditor[0],
                'amount': payment,
            })

        debtor[1] += payment
        creditor[1] -= payment

        if abs(debtor[1]) < CENT:
            i += 1
        if abs(creditor[1]) < CENT:
            j += 1

    return transactions
