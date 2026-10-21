"""Build an executive PDF briefing from the benchmark's verified article data."""
from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate, Flowable, Frame, Image, KeepTogether, PageBreak, PageTemplate,
    Paragraph, Spacer, Table, TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
TMP = ROOT / "tmp" / "pdfs"
OUT = ROOT / "output" / "pdf" / "AI-Assisted-Credit-Memo-Governance-Executive-Brief.pdf"
RESULTS = ROOT / "results"
TMP.mkdir(parents=True, exist_ok=True)
OUT.parent.mkdir(parents=True, exist_ok=True)

NAVY = colors.HexColor("#101827")
NAVY2 = colors.HexColor("#17243A")
INK = colors.HexColor("#182437")
MUTED = colors.HexColor("#5E7188")
CYAN = colors.HexColor("#13B8D5")
TEAL = colors.HexColor("#1D9C8A")
PALE = colors.HexColor("#EAF5F8")
PALEBLUE = colors.HexColor("#EEF2F8")
LINE = colors.HexColor("#D8E0E8")
AMBER = colors.HexColor("#E6A342")
RED = colors.HexColor("#D35E6A")
WHITE = colors.white

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="CoverEyebrow", fontName="Helvetica-Bold", fontSize=9, leading=13, textColor=CYAN, uppercase=True, spaceAfter=15, tracking=1.4))
styles.add(ParagraphStyle(name="CoverTitle", fontName="Helvetica-Bold", fontSize=29, leading=33, textColor=WHITE, spaceAfter=16))
styles.add(ParagraphStyle(name="CoverSub", fontName="Helvetica", fontSize=13, leading=19, textColor=colors.HexColor("#C8D5E5"), spaceAfter=15))
styles.add(ParagraphStyle(name="H1x", fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=NAVY, spaceBefore=0, spaceAfter=10, keepWithNext=True))
styles.add(ParagraphStyle(name="H2x", fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=NAVY2, spaceBefore=9, spaceAfter=5, keepWithNext=True))
styles.add(ParagraphStyle(name="Bodyx", fontName="Helvetica", fontSize=9.1, leading=13, textColor=INK, spaceAfter=6))
styles.add(ParagraphStyle(name="Smallx", fontName="Helvetica", fontSize=7.5, leading=10, textColor=MUTED, spaceAfter=4))
styles.add(ParagraphStyle(name="Calloutx", fontName="Helvetica-Bold", fontSize=11, leading=16, textColor=NAVY, spaceAfter=0))
styles.add(ParagraphStyle(name="KpiValue", fontName="Helvetica-Bold", fontSize=21, leading=24, textColor=NAVY, alignment=TA_LEFT))
styles.add(ParagraphStyle(name="KpiLabel", fontName="Helvetica", fontSize=7.5, leading=10, textColor=MUTED))
styles.add(ParagraphStyle(name="TableHeadx", fontName="Helvetica-Bold", fontSize=7.4, leading=9.2, textColor=WHITE))
styles.add(ParagraphStyle(name="TableCellx", fontName="Helvetica", fontSize=7.2, leading=9.2, textColor=INK))
styles.add(ParagraphStyle(name="TableCellBoldx", fontName="Helvetica-Bold", fontSize=7.2, leading=9.2, textColor=INK))
styles.add(ParagraphStyle(name="CoverFoot", fontName="Helvetica", fontSize=8, leading=12, textColor=colors.HexColor("#8EA4BC")))


def P(text: str, style: str = "Bodyx") -> Paragraph:
    return Paragraph(text, styles[style])


def header_footer(canvas, doc):
    canvas.saveState()
    w, h = letter
    if doc.page == 1:
        canvas.setFillColor(NAVY)
        canvas.rect(0, 0, w, h, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor("#16263B"))
        canvas.circle(w + 30, h - 70, 170, fill=1, stroke=0)
        canvas.setStrokeColor(colors.HexColor("#28445B"))
        canvas.setLineWidth(1)
        for radius in (135, 158, 181):
            canvas.circle(w + 32, h - 65, radius, fill=0, stroke=1)
        canvas.setFillColor(CYAN)
        canvas.roundRect(0.6*inch, 0.68*inch, 2.0*inch, 0.045*inch, 2, fill=1, stroke=0)
    else:
        canvas.setFillColor(NAVY)
        canvas.rect(0, h-0.38*inch, w, 0.38*inch, fill=1, stroke=0)
        canvas.setFillColor(CYAN)
        canvas.rect(0, h-0.38*inch, 0.10*inch, 0.38*inch, fill=1, stroke=0)
        canvas.setFont("Helvetica-Bold", 7.5)
        canvas.setFillColor(WHITE)
        canvas.drawString(0.63*inch, h-0.25*inch, "CREDIT MEMO GOVERNANCE  /  MEASURE")
        canvas.setFillColor(MUTED)
        canvas.setStrokeColor(LINE)
        canvas.line(0.62*inch, 0.55*inch, w-0.62*inch, 0.55*inch)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(0.62*inch, 0.36*inch, "Synthetic data only  ·  Research prototype  ·  October 2026")
        canvas.drawRightString(w-0.62*inch, 0.36*inch, f"{doc.page}")
    canvas.restoreState()


class BriefDocTemplate(BaseDocTemplate):
    def __init__(self, filename, **kwargs):
        super().__init__(filename, pagesize=letter, **kwargs)
        frame = Frame(0.68*inch, 0.72*inch, 7.14*inch, 9.82*inch, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0, id="normal")
        self.addPageTemplates([PageTemplate(id="brief", frames=frame, onPage=header_footer)])


def callout(text, bg=PALE, stripe=CYAN, width=7.14*inch, pad=12):
    t = Table([[P(text, "Calloutx")]], colWidths=[width])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,-1),bg), ("BOX",(0,0),(-1,-1),0.5,LINE),
        ("LINEBEFORE",(0,0),(0,-1),4,stripe), ("LEFTPADDING",(0,0),(-1,-1),pad+3),
        ("RIGHTPADDING",(0,0),(-1,-1),pad), ("TOPPADDING",(0,0),(-1,-1),pad),
        ("BOTTOMPADDING",(0,0),(-1,-1),pad),
    ]))
    return t


def kpi_cards(items):
    cells=[]
    for value,label,accent in items:
        box=Table([[P(value,"KpiValue")],[P(label,"KpiLabel")]],colWidths=[1.66*inch])
        box.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),PALEBLUE),("LINEBEFORE",(0,0),(0,-1),3,accent),("LEFTPADDING",(0,0),(-1,-1),9),("RIGHTPADDING",(0,0),(-1,-1),7),("TOPPADDING",(0,0),(-1,0),8),("BOTTOMPADDING",(0,0),(-1,0),1),("TOPPADDING",(0,1),(-1,1),0),("BOTTOMPADDING",(0,1),(-1,1),8)]))
        cells.append(box)
    row=Table([cells],colWidths=[1.76*inch]*len(cells),hAlign="LEFT")
    row.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),5),("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0)]))
    return row


def table(headers, rows, widths, font_size=7.2):
    data=[[P(h,"TableHeadx") for h in headers]]
    for row in rows:
        data.append([P(str(v),"TableCellx") for v in row])
    t=Table(data,colWidths=widths,repeatRows=1,hAlign="LEFT",splitByRow=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),NAVY2),("GRID",(0,0),(-1,-1),0.35,LINE),
        ("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),6),
        ("RIGHTPADDING",(0,0),(-1,-1),6),("TOPPADDING",(0,0),(-1,-1),5),
        ("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE,PALEBLUE]),
    ]))
    return t



class WorkflowDiagram(Flowable):
    """Vector flowchart showing the operational gate and offline benchmark path."""
    def __init__(self):
        super().__init__()
        self.width = 7.14 * inch
        self.height = 2.35 * inch

    def draw(self):
        c = self.canv
        w = self.width
        c.saveState()
        c.setFillColor(colors.HexColor("#F7FAFC"))
        c.setStrokeColor(LINE)
        c.roundRect(0, 0, w, self.height, 9, fill=1, stroke=1)

        def box(x, y, bw, bh, title, body, fill, stroke, title_color=NAVY):
            c.setFillColor(fill); c.setStrokeColor(stroke); c.setLineWidth(1)
            c.roundRect(x, y, bw, bh, 6, fill=1, stroke=1)
            title_lines=title.split("\n")
            c.setFillColor(title_color); c.setFont("Helvetica-Bold", 6.9)
            for i,line in enumerate(title_lines): c.drawCentredString(x+bw/2, y+bh-12-i*8, line)
            c.setFillColor(INK); c.setFont("Helvetica", 6.4)
            lines=body.split("\n")
            body_start=12+8*len(title_lines)+5
            for i,line in enumerate(lines): c.drawCentredString(x+bw/2, y+bh-body_start-i*8, line)

        def arrow(x1,y1,x2,y2,color=TEAL,dashed=False):
            c.setStrokeColor(color); c.setFillColor(color); c.setLineWidth(1.2)
            if dashed: c.setDash(3,2)
            c.line(x1,y1,x2,y2)
            c.setDash()
            import math
            a=math.atan2(y2-y1,x2-x1); size=4
            p=c.beginPath(); p.moveTo(x2,y2)
            p.lineTo(x2-size*math.cos(a-0.45),y2-size*math.sin(a-0.45))
            p.lineTo(x2-size*math.cos(a+0.45),y2-size*math.sin(a+0.45)); p.close()
            c.drawPath(p,fill=1,stroke=0)

        y=1.12*inch; bh=0.65*inch
        widths=[0.91*inch,1.08*inch,0.93*inch,1.05*inch,0.99*inch]
        xs=[0.12*inch,1.17*inch,2.39*inch,3.47*inch,4.77*inch]
        box(xs[0],y,widths[0],bh,"AI INTAKE\nAGENT","Borrower request\nFlag missing inputs",PALEBLUE,LINE)
        box(xs[1],y,widths[1],bh,"EXTRACTION\nLLM","16 values + evidence\nor NOT FOUND",colors.HexColor("#E7F6F9"),CYAN)
        box(xs[2],y,widths[2],bh,"FORMULA\nTIE-OUT","Check both years\nFlag missing / mismatch",PALEBLUE,LINE)
        box(xs[3],y,widths[3],bh,"GATE 1\nHUMAN REVIEW","Identity + period\nCompleteness + 2 values",colors.HexColor("#FFF5E8"),AMBER)
        box(xs[4],y,widths[4],bh,"FIVE RATIOS","Deterministic formulas\nOnly after approval",colors.HexColor("#E8F5F1"),TEAL)
        for i in range(4): arrow(xs[i]+widths[i]+2,y+bh/2,xs[i+1]-3,y+bh/2)

        # Human review branches: approve continues; send-back returns to extraction.
        gate_c=xs[3]+widths[3]/2
        c.setFont("Helvetica-Bold",6.2); c.setFillColor(TEAL); c.drawString(xs[4]+0.04*inch,y+bh+3,"APPROVE")
        c.setFillColor(AMBER); c.drawString(xs[2]+0.16*inch,y-10,"SEND BACK: reason + correction; max two returns, then escalate")
        arrow(gate_c,y-2,xs[1]+widths[1]/2,y-2,AMBER,True)
        c.setFont("Helvetica",6.5); c.setFillColor(MUTED)
        c.drawString(0.14*inch,0.73*inch,"V1 begins after intake: frozen fixed-schema statement + hidden QA truth; extraction and ratios scored offline.")
        c.setStrokeColor(colors.HexColor("#7D91A7")); c.setDash(3,2); c.roundRect(0.12*inch,0.12*inch,w-0.24*inch,0.48*inch,5,fill=0,stroke=1); c.setDash()
        c.setFont("Helvetica-Bold",6.7); c.setFillColor(MUTED)
        c.drawString(0.23*inch,0.40*inch,"NOT IN THIS PROTOTYPE: final credit decision remains with an accountable credit officer.")
        c.setFont("Helvetica",6.1); c.drawString(0.23*inch,0.24*inch,"Intake unmeasured; human Gate 1 decisions pending. Operational ratios still require approval.")
        c.restoreState()


def chart(name, width=6.55*inch):
    path=TMP/f"{name}.png"
    from PIL import Image as PILImage
    with PILImage.open(path) as im:
        iw,ih=im.size
    img=Image(str(path),width=width,height=width*ih/iw)
    img.hAlign="LEFT"
    return img


story=[]
# Cover
story += [Spacer(1,0.78*inch), P("AI GOVERNANCE RESEARCH SERIES  /  EXECUTIVE BRIEF", "CoverEyebrow"),
          P("Extending the AI-Assisted<br/>Credit Memo Case Study", "CoverTitle"),
          P("A controlled benchmark of source quality, model extraction, deterministic ratios, and human review.", "CoverSub"),
          P("Research extension of KhanShrz's original case study; original workflow and findings attributed to its author.", "CoverFoot"), Spacer(1,0.26*inch)]
story.append(callout("KEY TAKEAWAY<br/><br/>A model can copy every displayed figure correctly while the resulting ratios still disagree with clean financials. In this controlled synthetic test, input quality shaped the downstream numbers more than the choice among the pilot models.",bg=colors.HexColor("#E7F6F9"),stripe=CYAN,pad=15))
story += [Spacer(1,0.28*inch), P("MEASURE  →  STANDARDIZE  →  OPTIMIZE  →  INNOVATE  →  SCALE", "CoverEyebrow"),
          P("This edition reports Measure only. The remaining stages are a research plan, not completed work.", "CoverSub"),
          Spacer(1,2.65*inch), P("October 2026  ·  Synthetic data only  ·  Research prototype", "CoverFoot"), PageBreak()]

# Executive summary
story += [P("Executive summary","H1x"),P("KhanShrz's original case study built a linear workflow for preparing financial data behind a commercial credit memo: an AI intake agent captures the request, a retrieval agent extracts figures, formulas check and calculate, and a human reviewer approves the extracted data before ratios are used. Our Benchmark V1 starts after intake to measure source quality, extraction reliability, and control gaps. The AI does not make the credit decision.")]
story.append(kpi_cards([("10,000","controlled synthetic records",CYAN),("55.0%","overall clean-latent ratio match",AMBER),("24","records in matched model pilot",TEAL),("$1.83 / $2","paid spend / authorized cap",RED)]))
story += [Spacer(1,10),P("Three findings for decision-makers","H2x"),
          P("<b>1. Source quality propagates.</b> Simulator extraction matched every displayed value. Clean-latent ratio agreement was 17.6%, 47.4%, and 100% across preassigned 50%, 75%, and 100% source-quality tiers."),
          P("<b>2. Controls have different jobs.</b> Deterministic formulas remove arithmetic variability. A tie-out checks consistency; it does not prove that a value is authentic or mapped to the right line item. Gate 1 is where a human checks the source and can send the extraction back."),
          P("<b>3. A completed API job can still fail the task.</b> Two 10,000-request batches completed at the provider, but the chosen output-token cap yielded zero schema-complete extractions. Those batches provide no valid model accuracy comparison."),
          callout("Decision boundary: this is a controlled research baseline, not an independent validation and not approval for production or credit decisions.",bg=PALE,stripe=TEAL),
          P("Evidence at a glance","H2x")]
story.append(table(["Evidence","Observed result","What it supports"],[
    ("10k deterministic quality-mix","320,000 / 320,000 displayed fields matched; 55.01% clean-latent ratio agreement overall","Controlled source defects can flow into formula outputs"),
    ("24-record model pilot","Three routes on the identical stratified cohort; samples too small to rank","Screening signals only"),
    ("1M deterministic simulator","100% agreement; 80.52 seconds","Deterministic pipeline scale only, not LLM inference"),
    ("10k provider batches","20,000 provider completions; 0 schema-complete records","Output-integrity/configuration failure"),
],[1.35*inch,2.6*inch,3.19*inch]))
story.append(PageBreak())

# Study and source-quality finding
story += [P("The question: what happens when the source is wrong?","H1x"),
          P("We generated one frozen corpus of 10,000 synthetic statements and assigned each record a known source-quality tier before inference. Each record contains 32 current- and prior-year numeric values. Exactly 16, 24, or 32 values agree with a separately stored clean record at the 50%, 75%, and 100% tiers. Mutations were planned across five defect classes and eight statement layouts."),
          P("Models see only the statement and record ID. The QA sidecar and clean truth are withheld. We score extraction against the values printed in the statement separately from ratios against the clean latent values."),
          chart("source-quality-to-ratios"),
          P("<b>Figure 1.</b> All displayed values were read exactly by the deterministic simulator. Ratio agreement with the clean underlying record falls as the preassigned source quality declines. Error percentages are controlled stress points, not estimates of defect prevalence in actual filings.","Smallx"),
          P("Why this matters","H2x"),
          P("The five ratios remain deterministic and follow the original workflow. That makes the math repeatable, but it does not repair an incorrect input. A consistency check can fail on some defects, yet a coherent-looking set of wrong figures can still pass. The result argues for source evidence and semantic checks alongside formula checks."),
          P("The quality-mix cohort recorded 11,721 tie-out failures and 6,541 record-level control flags. These reflect intentionally planted data defects and should not be interpreted as real-world error rates or AI failures."),
          PageBreak()]

# Model results and output integrity
story += [P("Model results: promising pilot, invalid full batches","H1x"),
          P("Three model routes completed a matched pilot on the same 24 records: eight at each source tier, spanning all eight layouts. The sample is exploratory. Free/local token reporting and route latency differ, so numbers are descriptive rather than a ranking.")]
story.append(table(["Route","Source field match<br/>50 / 75 / 100%","Clean-latent ratio match<br/>50 / 75 / 100%","Time / tokens","Gate 1 flags"],[
    ("DeepSeek V4.1 Flash<br/>OpenCode, free","100 / 100 / 100%","16.25 / 43.75 / 100%","190.1 s<br/>395,075","17"),
    ("MiniMax M3.1 Flash<br/>OpenRouter, free","100 / 100 / 100%","16.25 / 43.75 / 100%","318.4 s<br/>59,775","19"),
    ("Qwen 3.5 9B<br/>Ollama, local","99.22 / 99.61 / 99.22%","13.75 / 45.00 / 87.50%","427.9 s<br/>40,500","24"),
],[1.45*inch,1.42*inch,1.52*inch,1.28*inch,1.47*inch]))
story += [Spacer(1,8),chart("matched-model-quality-pilot"),
          P("<b>Figure 2.</b> Same cohort and tier sizes for each model. The 24-row sample does not justify a production model selection.","Smallx"),
          P("Full-cohort batch attempt","H2x"),
          P("To compare the whole 10,000-row cohort, we submitted independent requests to GPT-OSS 20B Batch and Ministral 8B Batch. Both provider jobs completed all requests. A 640-token output cap truncated the JSON: GPT-OSS had 10,000 parse failures; Ministral had 9,461 parse failures and 539 parsed but incomplete responses. Both produced zero schema-complete records."),
          chart("batch-output-integrity"),
          P("<b>Figure 3.</b> Provider completion was 100%; usable schema output was 0%. Therefore accuracy is unavailable for these batches, not zero.","Smallx"),
          table(["Model","Prompt tokens","Completion tokens","Schema complete","Cost"],[
              ("GPT-OSS 20B Batch","6,956,176","6,400,000","0 / 10,000","$0.883748"),
              ("Ministral 8B Batch","8,413,151","6,288,310","0 / 10,000","$0.948817"),
          ],[1.75*inch,1.35*inch,1.48*inch,1.28*inch,1.38*inch]),
          Spacer(1,6),
          callout("Spend control: $1.834534 of the $2.00 cap was spent. $0.165466 remains, which cannot fund a corrected full 10k paid pass. The next full paid run requires a newly approved budget.",bg=colors.HexColor("#FFF5E8"),stripe=AMBER),
          PageBreak()]

# Workflow, human role, scale
story += [P("Controls and the human checkpoint","H1x"),
          P("The workflow assigns different responsibilities to the model, formulas, and reviewer. This makes it possible to ask not only whether a number is right, but where the control path caught or missed an error."),
          P("Architecture and approval flow","H2x"),
          WorkflowDiagram(), Spacer(1,8),
          table(["Stage","Owner","Control purpose"],[
              ("Data retrieval","One LLM, schema-constrained","Copy each figure from the filing; cite evidence or return NOT FOUND; do no arithmetic"),
              ("Gross-margin tie-out","Formula","Test arithmetic consistency in both years"),
              ("Gate 1","Human reviewer","Check borrower, period, completeness, tie-out, and two cited values; approve or send back"),
              ("Five ratios","Deterministic formulas","Calculate only after human approval in the operational flow"),
              ("Credit decision","Accountable credit officer","Outside this prototype and benchmark"),
          ],[1.15*inch,1.55*inch,4.44*inch]),
          P("The benchmark creates blinded Gate 1 worksheets, but reviewer decisions are blank. Human review effectiveness, correction quality, false approvals, and review time have not yet been measured. Offline ratio calculation is only for benchmark scoring; it does not bypass Gate 1 in the source workflow."),
          P("Deterministic scale evidence","H2x"),
          chart("simulator-scale"),
          P("<b>Figure 4.</b> Local deterministic simulator timing across record prefixes (log axes). The one-million-record run completed in 80.52 seconds at roughly 12,420 records per second. No million-record LLM inference run has been completed.","Smallx"),
          P("The original prototype's key failures reinforce the same control boundary: fabricated operating income with a real citation; lease interest mapped as interest expense; a tie-out that passed on zero data; a reviewer approval with all figures missing; standalone-versus-workflow regression failure; source-version drift; a skippable human question; and an unflagged injection attempt. Controls were added and retested, but the case study itself notes that the model-generated dataset remains the dependency beneath downstream checks."),
          PageBreak()]

# Publication roadmap
story += [P("What the next articles will test","H1x"),
          P("The research will advance one stage at a time. Planned studies will be labeled as plans until their tests run and are reviewed. Every cross-model comparison will keep cohort, schema, and hidden truth fixed; every article will disclose failures, cost, and uncertainty."),
          table(["Article / stage","Research question","Evidence shared / gate to proceed"],[
              ("1. Measure baseline<br/><b>Current</b>","How do source tiers affect extraction and ratios?","10k deterministic run; matched 24-row pilot; invalid batch attempt; spend ledger"),
              ("2. Complete matched model comparison<br/><b>Measure</b>","How do models perform on the same 10k cohort with a valid output cap?","Tiny schema smoke first; new budget required for paid full pass; report exact hashes and failed outputs"),
              ("3. Gate 1 effectiveness<br/><b>Measure</b>","What defects do blinded reviewers detect, correct, or approve?","Human reviewers; accuracy, false approvals, send-backs, escalations, review time"),
              ("4. Financial data contract<br/><b>Standardize</b>","Do approved mappings for units, periods, evidence, and line items reduce ambiguity?","Versioned data dictionary and predeclared tests; source definitions remain explicit"),
              ("5. Workflow efficiency<br/><b>Optimize</b>","Can one change at a time reduce latency/cost without quality loss?","Same-cohort measures, token count, output validity, controls and reviewability"),
              ("6. Bounded oversight check<br/><b>Innovate</b>","Does an independent second pass find errors missed by current controls?","Incremental detection, false alarms, added cost and human workload; linear baseline retained"),
              ("7. Operational scale<br/><b>Scale</b>","How do validated routes behave from 100 to 1M records?","Throughput, latency, failures, budget and human review capacity; expand only after smaller gates pass"),
          ],[1.65*inch,2.15*inch,3.34*inch]),
          Spacer(1,9),
          callout("No swarms, JEV routing, model cascade, or alternate decision architecture are part of the current experiment. Those questions can be considered only after the single-model baseline, standardized data contract, and human checkpoint are measured.",bg=PALE,stripe=TEAL),
          PageBreak()]

# Caveats and definitions
story += [P("Evidence limits and definitions","H1x"),
          P("This study uses synthetic financial statements with deliberately assigned defects. The filing-like layouts remain simpler than real 10-Ks. We have not established full filing search, citation fidelity, footnote/segment interpretation, restatement handling, company-wide generalization, or production readiness. A small sample is not a model ranking; an invalid response is not a valid accuracy score."),
          P("Five ratios retained from the source workflow","H2x"),
          table(["Ratio","Formula"],[
              ("Interest coverage","Operating income ÷ interest expense"),
              ("Current ratio","Total current assets ÷ total current liabilities"),
              ("Debt-to-equity","(Current portion of long-term debt + long-term debt) ÷ equity"),
              ("Total debt / EBITDA","(Current portion of long-term debt + long-term debt) ÷ (operating income + depreciation, amortization, and other)"),
              ("Net margin","Net income ÷ total revenue"),
          ],[1.65*inch,5.49*inch]),
          P("Total debt excludes leases. Interest expense is the specifically labeled line item and is positive. EBITDA follows the source definition: operating income plus “depreciation, amortization, and other” from the cash-flow statement. The gross-margin tie-out is gross margin − research and development − sales and marketing − general and administrative − operating income = 0. These definitions describe this prototype; they are not a universal credit policy."),
          P("Reproducibility and safeguards","H2x"),
          P("The seed is 20261020. Input and truth are saved separately. The 10,000-record quality-mix input SHA-256 is d288e317576cc95a3ccaaa8ffd80cd0da42ac0a6b549d22fb595c42e5fbc0bbb; truth SHA-256 is ed89602f6a34317187521b3dd4aa74dc9ac4724a58899f607e596d1efae6f331. The model never receives the truth or QA sidecar. The article, CSV outputs, charts, model responses, and spend ledger are retained under the benchmark project. API keys remain in environment variables; no borrower data is used."),
          P("Original case study: <i>Governing an AI-Assisted Credit Memo Workflow: A Case Study</i>, October 13, 2026. This brief references the 19-page repository edition, which includes a Section 8 on independent review absent from a separately circulated 15-page version. Original workflow and test artifacts remain in the repository; the benchmark records are synthetic.","Smallx"),
          Spacer(1,10),
          callout("Research prototype only. Not credit, investment, or financial advice. Not independently validated and not approved for production use.",bg=colors.HexColor("#FFF0F1"),stripe=RED),
          Spacer(1,12),P("Full methodology, detailed tables, source notes, and the interactive chart are in the companion article and benchmark dashboard.","Smallx")]

doc=BriefDocTemplate(str(OUT),title="Extending the AI-Assisted Credit Memo Case Study - Executive Brief",author="Credit Memo Governance Research Series",subject="Research extension of KhanShrz's case study: Measure-stage benchmark findings and planned research")
doc.build(story)
print(OUT)
