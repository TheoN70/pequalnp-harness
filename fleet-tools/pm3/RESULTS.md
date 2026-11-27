# PM 3x3 refute family (Normal4 leads). Statements: ¬ ∃ C normal-form, size ≤ k, opening pinned.
# SAT + normal_form_ok = statement FALSE -> statement_seems_false. UNSAT (pinned, no fLex) = TRUE -> no Lean route at n=9 -> out_of_time.
# Runs: pm3.py <k> <opening>, capmem 3G, 19 min, one core each. Outputs <id>.out.
| id | k | opening | result |
|---|---|---|---|
| 27406 | 12 | and,0,4 or,1,5 | TRUE, PR #41374 (27763 route, start P=2,Q=3) |
| 27551 | 11 | or,0,4 and,0,5 | TRUE, PR #41256 |
| 27543 | 11 | or,0,1 and,5,9 | TRUE, PR #41219 (27743 route) |
| 27462 | 12 | and,0,4 or,8,9 | open: 27763 count has slack 1 here (see HOWTO); SAT undecided |
| 27408 | 12 | and,0,4 or,1,8 | TRUE, PR #41432 |
| 27539 | 11 | or,0,1 and,3,9 | TRUE, PR #41236 |
| (none) | 12 | no opening, fLex kept | ../27406/out_12_0.txt: UNSAT here = every k ≤ 12 step of the family is TRUE |
| 27176 (POSITIVE, Normal5) | 11 | and,0,1 not,2 | 27176.out, c27176.out |
| 27748 | 12 | or,0,1 or,2,3 (positive: SAT = proof) | c27748.out (Normal3) |
| 27198 (POSITIVE, Normal) | 11 | and,0,4 and,1,8 | c27198.out |
| 27684 | 11 (positive side) | or,0,1 or,2,9 | FALSE: both gates constant under x0=1, tail <= 9 < 10 (L_meta_27743.lower); released statement_seems_false (Normal6). pm3c killed at iter 5 |
| 27607 | 12 | or,0,1 and,5,9 | TRUE by the 27743 route with stable f := ∀ y, y4 = (y4&&y0) → f(plug y)=f(off y) (wire 10 = x5&(x0|x1) is then stable, x0 and wire 9 constant under x0=1); Normal6, PR #41624 |
| 27624 | 12 (some) | or,0,4 and,1,8 | FALSE by route 2 (start P=2 Q=3 as 27406); released statement_seems_false (Normal6); twin 27625 = adapt 27763 |
