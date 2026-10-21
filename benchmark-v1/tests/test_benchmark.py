import sys, unittest
sys.path.insert(0,'src')
from benchmark import generate, extract, ratios
class BenchmarkTests(unittest.TestCase):
 def test_seed_reproducible_and_tieout(self):
  a=generate(4,7); b=generate(4,7); self.assertEqual([x['truth'] for x in a],[x['truth'] for x in b])
  for r in a:
   t=r['truth']; self.assertEqual(t['gross_margin'][0]-t['research_and_development'][0]-t['sales_and_marketing'][0]-t['general_and_administrative'][0],t['operating_income'][0])
 def test_parser_excludes_lease_interest(self):
  r=generate(1,8)[0]; x,_,_=extract(r); self.assertEqual(x['interest_expense']['cy'],r['truth']['interest_expense'][0]); self.assertNotEqual(x['interest_expense']['cy'],999)
 def test_all_fields_match_independent_truth_with_negative_values(self):
  for r in generate(250,20261020):
   x,_,_=extract(r)
   for k in __import__('benchmark').FIELDS:
    self.assertEqual((x[k]['cy'],x[k]['py']),tuple(r['truth'][k]))
 def test_ratio_values_against_independent_formulas(self):
  r=generate(1,11)[0]; x,_,_=extract(r); got=ratios(x)
  for j,year in enumerate(('cy','py')):
   t=r['truth']; debt=t['current_portion_ltd'][j]+t['long_term_debt'][j]
   expected=(t['operating_income'][j]/t['interest_expense'][j],t['total_current_assets'][j]/t['total_current_liabilities'][j],debt/t['stockholders_equity'][j],debt/(t['operating_income'][j]+t['depreciation_amortization'][j]),t['net_income'][j]/t['total_revenue'][j])
   self.assertEqual(tuple(got[j].values()),expected)
 def test_ratio_count(self):
  x,_,_=extract(generate(1,9)[0]); self.assertEqual(len(ratios(x)),2); self.assertEqual(len(ratios(x)[0]),5)
 def test_filing_like_layout_variants_recover_all_ground_truth(self):
  for r in generate(80,20261020,realistic=True):
   x,_,_=extract(r)
   for k in __import__('benchmark').FIELDS:
    self.assertEqual((x[k]['cy'],x[k]['py']),tuple(r['truth'][k]),(r['id'],k,r['text']))
 def test_filing_like_distractors_do_not_replace_consolidated_revenue_or_interest(self):
  r=generate(8,20261020,realistic=True)[0]
  x,_,_=extract(r)
  self.assertEqual(x['total_revenue']['cy'],r['truth']['total_revenue'][0])
  self.assertEqual(x['interest_expense']['cy'],r['truth']['interest_expense'][0])
 def test_quality_mix_is_exactly_baked_into_each_record(self):
  for tier in (50,75,100):
   rows=[r for r in generate(300,20261020,quality_mix=True) if r['quality_tier']==tier]
   expected={50:16,75:24,100:32}[tier]
   self.assertEqual(len(rows),100)
   for row in rows:
    correct=sum(row['truth'][k][j]==row['latent_truth'][k][j] for k in __import__('benchmark').FIELDS for j in (0,1))
    self.assertEqual(correct,expected)
if __name__=='__main__': unittest.main()
