"""
Core business logic: turning a list of member balances into the minimum
number of payments needed to settle all debts (a classic greedy
"minimum cash flow" algorithm).
"""
from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _excel_cell(reference, value, cell_type=None, style=None):
    """Return a minimal SpreadsheetML cell using inline text or numbers."""
    style_attr = f' s="{style}"' if style is not None else ''
    if cell_type == 'number':
        return f'<c r="{reference}"{style_attr}><v>{value}</v></c>'
    return f'<c r="{reference}"{style_attr} t="inlineStr"><is><t>{escape(str(value))}</t></is></c>'


def build_trip_workbook(trip, expenses):
    """Create a full .xlsx report for one trip, including settlement details."""
    expense_rows = list(expenses)
    suggested_settlements = simplify_settlements(trip.members.all())
    recorded_settlements = list(trip.settlements.select_related('from_member', 'to_member'))
    rows = []
    rows.append('<row r="1">' + _excel_cell('A1', f'{trip.name} — Expense Report', style=1) + '</row>')
    rows.append('<row r="2">' + _excel_cell('A2', f'Destination: {trip.destination or "Not set"}') + '</row>')
    rows.append('<row r="3">' + _excel_cell('A3', f'Period: {trip.start_date or "Not set"} to {trip.end_date or "Not set"}') + '</row>')
    rows.append('<row r="5">' + ''.join(_excel_cell(f'{column}5', heading, style=2) for column, heading in zip('ABCDE', ['Date', 'Expense', 'Paid by', 'Notes', f'Amount ({trip.currency})'])) + '</row>')
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
        '<row r="7">' + ''.join(_excel_cell(f'{column}7', heading, style=2) for column, heading in zip('ABC', ['Member', f'Amount paid ({trip.currency})', f'Balance ({trip.currency})'])) + '</row>',
    ]
    for index, member in enumerate(trip.members.all(), start=8):
        summary_rows.append('<row r="{0}">'.format(index) + ''.join([
            _excel_cell(f'A{index}', member.name),
            _excel_cell(f'B{index}', member.total_paid, 'number', 3),
            _excel_cell(f'C{index}', member.adjusted_balance, 'number', 3),
        ]) + '</row>')

    settlement_rows = []
    settlement_rows.append('<row r="1">' + _excel_cell('A1', f'{trip.name} — Settlements', style=1) + '</row>')
    settlement_rows.append('<row r="3">' + ''.join(_excel_cell(f'{column}3', heading, style=2) for column, heading in zip('ABCDE', ['Status', 'From', 'To', f'Amount ({trip.currency})', 'Date / note'])) + '</row>')
    row_index = 4
    for settlement in suggested_settlements:
        settlement_rows.append('<row r="{0}">'.format(row_index) + ''.join([
            _excel_cell(f'A{row_index}', 'Suggested'),
            _excel_cell(f'B{row_index}', settlement['from'].name),
            _excel_cell(f'C{row_index}', settlement['to'].name),
            _excel_cell(f'D{row_index}', settlement['amount'], 'number', 3),
            _excel_cell(f'E{row_index}', 'Pending settlement'),
        ]) + '</row>')
        row_index += 1
    for settlement in recorded_settlements:
        settlement_rows.append('<row r="{0}">'.format(row_index) + ''.join([
            _excel_cell(f'A{row_index}', 'Paid'),
            _excel_cell(f'B{row_index}', settlement.from_member.name),
            _excel_cell(f'C{row_index}', settlement.to_member.name),
            _excel_cell(f'D{row_index}', settlement.amount, 'number', 3),
            _excel_cell(f'E{row_index}', settlement.settled_on.isoformat()),
        ]) + '</row>')
        row_index += 1
    if row_index == 4:
        settlement_rows.append('<row r="4">' + _excel_cell('A4', 'No settlements recorded or required.') + '</row>')

    def sheet_xml(row_data, widths):
        return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                f'<cols>{widths}</cols><sheetData>{"".join(row_data)}</sheetData></worksheet>')

    styles = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><numFmts count="1"><numFmt numFmtId="164" formatCode="{trip.currency_symbol}#,##0.00"/></numFmts><fonts count="2"><font><sz val="11"/><name val="Aptos"/></font><font><b/><sz val="11"/><name val="Aptos"/></font></fonts><fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="DCEBFF"/><bgColor indexed="64"/></patternFill></fill></fills><borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders><cellXfs count="5"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/><xf numFmtId="0" fontId="1" fillId="0" borderId="0"/><xf numFmtId="0" fontId="1" fillId="2" borderId="0"/><xf numFmtId="164" fontId="0" fillId="0" borderId="0" applyNumberFormat="1"/><xf numFmtId="164" fontId="1" fillId="2" borderId="0" applyNumberFormat="1"/></cellXfs></styleSheet>'''
    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/worksheets/sheet3.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>'''
    relationships = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'''
    workbook = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Expenses" sheetId="1" r:id="rId1"/><sheet name="Summary" sheetId="2" r:id="rId2"/><sheet name="Settlements" sheetId="3" r:id="rId3"/></sheets></workbook>'''
    workbook_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet3.xml"/><Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>'''
    output = BytesIO()
    with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
        archive.writestr('[Content_Types].xml', content_types)
        archive.writestr('_rels/.rels', relationships)
        archive.writestr('xl/workbook.xml', workbook)
        archive.writestr('xl/_rels/workbook.xml.rels', workbook_rels)
        archive.writestr('xl/styles.xml', styles)
        archive.writestr('xl/worksheets/sheet1.xml', sheet_xml(rows, '<col min="1" max="1" width="14" customWidth="1"/><col min="2" max="2" width="28" customWidth="1"/><col min="3" max="3" width="20" customWidth="1"/><col min="4" max="4" width="36" customWidth="1"/><col min="5" max="5" width="16" customWidth="1"/>'))
        archive.writestr('xl/worksheets/sheet2.xml', sheet_xml(summary_rows, '<col min="1" max="1" width="28" customWidth="1"/><col min="2" max="3" width="22" customWidth="1"/>'))
        archive.writestr('xl/worksheets/sheet3.xml', sheet_xml(settlement_rows, '<col min="1" max="1" width="15" customWidth="1"/><col min="2" max="3" width="22" customWidth="1"/><col min="4" max="4" width="18" customWidth="1"/><col min="5" max="5" width="22" customWidth="1"/>'))
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


def build_trip_pdf(trip, expenses):
    """Create a clean, printable trip report PDF with all financial details."""
    output = BytesIO()
    document = SimpleDocTemplate(
        output, pagesize=A4, rightMargin=15 * mm, leftMargin=15 * mm,
        topMargin=15 * mm, bottomMargin=16 * mm,
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle('ReportTitle', parent=styles['Title'], fontName='Helvetica-Bold', fontSize=25, leading=29, textColor=colors.HexColor('#17372c'), spaceAfter=3)
    subtitle = ParagraphStyle('ReportSubtitle', parent=styles['Normal'], fontSize=9.5, leading=14, textColor=colors.HexColor('#667c72'))
    section = ParagraphStyle('ReportSection', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=13, leading=17, textColor=colors.HexColor('#168a5b'), spaceBefore=15, spaceAfter=7)
    body = ParagraphStyle('ReportBody', parent=styles['Normal'], fontSize=8.5, leading=12, textColor=colors.HexColor('#263d34'))
    small = ParagraphStyle('ReportSmall', parent=body, fontSize=7.8, leading=10)
    right = ParagraphStyle('ReportRight', parent=body, alignment=TA_RIGHT)
    center = ParagraphStyle('ReportCenter', parent=body, alignment=TA_CENTER)

    def p(value, style=body):
        return Paragraph(escape(str(value or '—')), style)

    def money(value):
        return f'{trip.currency_symbol}{value:,.2f}'

    def table(data, widths, header=True):
        result = Table(data, colWidths=widths, repeatRows=1 if header else 0, hAlign='LEFT')
        commands = [
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), .35, colors.HexColor('#DCECE3')),
            ('LEFTPADDING', (0, 0), (-1, -1), 6), ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]
        if header:
            commands += [('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#168A5B')), ('TEXTCOLOR', (0, 0), (-1, 0), colors.white)]
        result.setStyle(TableStyle(commands))
        return result

    expense_rows = list(expenses)
    members = list(trip.members.all())
    suggestions = simplify_settlements(members)
    recorded = list(trip.settlements.select_related('from_member', 'to_member'))
    period = f'{trip.start_date or "Dates not set"} — {trip.end_date or "Dates not set"}' if trip.start_date else 'Dates not set'

    story = [
        Paragraph('TRIPSPLIT REPORT', ParagraphStyle('Overline', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, textColor=colors.HexColor('#168a5b'), leading=11, spaceAfter=2)),
        Paragraph(escape(trip.name), title),
        Paragraph(f'{escape(trip.destination or "Destination not set")} &nbsp; • &nbsp; {period} &nbsp; • &nbsp; {trip.currency} ({trip.currency_symbol})', subtitle),
        Spacer(1, 10),
    ]
    overview = [
        [p('TOTAL SPENT', center), p('EQUAL SHARE', center), p('TRAVEL CREW', center), p('EXPENSES', center)],
        [p(money(trip.total_expense), ParagraphStyle('Metric', parent=center, fontName='Helvetica-Bold', fontSize=14, textColor=colors.HexColor('#17372c'))), p(money(trip.per_person_share), ParagraphStyle('Metric2', parent=center, fontName='Helvetica-Bold', fontSize=14, textColor=colors.HexColor('#17372c'))), p(str(trip.member_count), ParagraphStyle('Metric3', parent=center, fontName='Helvetica-Bold', fontSize=14, textColor=colors.HexColor('#17372c'))), p(str(len(expense_rows)), ParagraphStyle('Metric4', parent=center, fontName='Helvetica-Bold', fontSize=14, textColor=colors.HexColor('#17372c')))],
    ]
    overview_table = Table(overview, colWidths=[45 * mm] * 4)
    overview_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F0FAF4')), ('BOX', (0, 0), (-1, -1), .6, colors.HexColor('#CBEAD8')),
        ('INNERGRID', (0, 0), (-1, -1), .4, colors.HexColor('#DCECE3')), ('TOPPADDING', (0, 0), (-1, -1), 7), ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
    ]))
    story.extend([overview_table, Paragraph('Member balances', section)])
    member_data = [[p('MEMBER', small), p('PAID', small), p('FAIR SHARE', small), p('CURRENT BALANCE', small)]]
    for member in members:
        balance = member.adjusted_balance
        label = f'Owed {money(balance)}' if balance > 0 else f'Owes {money(abs(balance))}' if balance < 0 else 'Settled up'
        member_data.append([p(member.name), p(money(member.total_paid), right), p(money(member.fair_share), right), p(label, right)])
    if not members:
        member_data.append([p('No members added yet.'), '', '', ''])
    story.append(table(member_data, [52 * mm, 37 * mm, 40 * mm, 51 * mm]))

    story.append(Paragraph('Expense ledger', section))
    expense_data = [[p('DATE', small), p('EXPENSE', small), p('PAID BY', small), p('NOTES', small), p('AMOUNT', small)]]
    for expense in expense_rows:
        expense_data.append([p(expense.date), p(expense.title), p(expense.paid_by.name), p(expense.notes or '—', small), p(money(expense.amount), right)])
    if not expense_rows:
        expense_data.append([p('No expenses added yet.'), '', '', '', ''])
    story.append(table(expense_data, [24 * mm, 45 * mm, 29 * mm, 53 * mm, 29 * mm]))

    story.append(Paragraph('Settle up plan', section))
    suggested_data = [[p('FROM', small), p('TO', small), p('AMOUNT', small), p('STATUS', small)]]
    for item in suggestions:
        suggested_data.append([p(item['from'].name), p(item['to'].name), p(money(item['amount']), right), p('Suggested payment')])
    if not suggestions:
        suggested_data.append([p('Everyone is settled up — no payments required.'), '', '', ''])
    story.append(table(suggested_data, [48 * mm, 48 * mm, 37 * mm, 47 * mm]))

    story.append(Paragraph('Payment history', section))
    payment_data = [[p('DATE', small), p('FROM', small), p('TO', small), p('AMOUNT', small), p('STATUS', small)]]
    for settlement in recorded:
        payment_data.append([p(settlement.settled_on), p(settlement.from_member.name), p(settlement.to_member.name), p(money(settlement.amount), right), p('Paid')])
    if not recorded:
        payment_data.append([p('No recorded payments yet.'), '', '', '', ''])
    story.append(table(payment_data, [27 * mm, 39 * mm, 39 * mm, 33 * mm, 42 * mm]))

    def add_footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor('#DCECE3'))
        canvas.line(15 * mm, 11 * mm, A4[0] - 15 * mm, 11 * mm)
        canvas.setFillColor(colors.HexColor('#667C72'))
        canvas.setFont('Helvetica', 7.5)
        canvas.drawString(15 * mm, 7 * mm, 'TripSplit • Shared travel made simple')
        canvas.drawRightString(A4[0] - 15 * mm, 7 * mm, f'Page {doc.page}')
        canvas.restoreState()

    document.build(story, onFirstPage=add_footer, onLaterPages=add_footer)
    return output.getvalue()
