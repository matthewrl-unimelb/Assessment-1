# Retrieval evaluation

Embedding model `text-embedding-3-large`, top-4 retrieval, 16 answerable test questions + 2 out-of-scope questions.

| Strategy | Chunks | Hit@1 | Hit@4 | Mean rank of first hit |
|---|---|---|---|---|
| A. Naive (150-word windows) | 22 | 7/16 | 13/16 | 1.69 |
| B. Structured, text only | 14 | 9/16 | 13/16 | 1.38 |
| C. Structured + context headers | 14 | 11/16 | 15/16 | 1.33 |

## Per-question results (rank of first chunk containing the answer; – = missed)

| Q | Question | A | B | C |
|---|---|---|---|---|
| Q01 | What fee did Campbell Limited agree to pay Independent? | 1 | 1 | 1 |
| Q02 | How much extra income was Cameron assessed on for 1965 and 1966? | 2 | 2 | 1 |
| Q03 | How did Diplock LJ define a sham? | 1 | 1 | 1 |
| Q04 | Why did J. K. Campbell want to deal with a company instead of the three men personally? | 1 | 3 | 2 |
| Q05 | Why was Cameron given the title of sales manager after he resigned? | 1 | 1 | 1 |
| Q06 | Could Cameron have sued Campbell Limited for the 15% fee? | 2 | 1 | 2 |
| Q07 | Did it matter that the arrangement saved tax? | 1 | 1 | 1 |
| Q08 | What did the Minister argue on the appeal? | – | 2 | 1 |
| Q09 | Why were the employment law cases cited by the Minister not relevant? | 3 | 1 | 1 |
| Q10 | What did the three men do with the bonus money they received in 1966? | 1 | 1 | 1 |
| Q11 | What happened to Symon's shares in Independent? | 1 | – | – |
| Q12 | Which judges heard the appeal? | 4 | 1 | 2 |
| Q13 | What was Cameron's job before the new arrangement? | 2 | – | 1 |
| Q14 | When was Independent Management Ltd. incorporated? | 2 | 1 | 1 |
| Q15 | Who owned Campbell Limited? | – | – | 3 |
| Q16 | Was the trial judge's finding based on Cameron's own evidence? | – | 2 | 1 |
| Q17 | What was Cameron's annual salary? *(out of scope)* | sim 0.449 | sim 0.402 | sim 0.433 |
| Q18 | Would the general anti-avoidance rule in section 245 change the result? *(out of scope)* | sim 0.382 | sim 0.378 | sim 0.388 |

For strategy C, the best similarity averaged 0.461 on answerable questions vs 0.410 on out-of-scope ones.
