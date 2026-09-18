<style>
a {
    text-decoration: none;
    color: #464feb;
}
tr th, tr td {
    border: 1px solid #e6e6e6;
}
tr th {
    background-color: #f5f5f5;
}
</style>

# 17 — Concise Literature Review: Verifying Equality of SQL Query Results

> Background reading for the correctness gate used in
> [12 — Darwin Warehouse Build Speedup](12-Darwin-Warehouse-Build-Speedup.md).
> That gate is a concrete instance of the **exact multiset reconciliation**
> problem surveyed here.

## 1. Problem definition

Verifying that two executed SQL queries produce **exactly the same dataset** is
best formulated as **typed multiset (bag) equality** rather than ordinary set
equality.

Two materialised results $R_A$ and $R_B$ are strictly equal when their schemas
match, $\text{Schema}(R_A) = \text{Schema}(R_B)$, and for every possible tuple
$t$:

$$\text{count}_{R_A}(t) = \text{count}_{R_B}(t)$$

This definition captures:

- schema and SQL data types;
- values;
- `NULL` semantics;
- duplicate multiplicities;
- precision, scale and collation;
- floating-point semantics.

Row ordering is normally excluded because relational results have no guaranteed
order unless an explicit deterministic `ORDER BY` is part of the output contract.

---

## 2. Exact relational comparison

The most direct approach is **relational difference**. Where supported, the
natural formulation is:

```sql
(A EXCEPT ALL B)
UNION ALL
(B EXCEPT ALL A)
```

The two datasets are equal iff the result is empty.

`EXCEPT ALL` is important because ordinary `EXCEPT` applies set semantics and
removes duplicates. Consequently, ordinary bidirectional `EXCEPT` cannot
distinguish:

```text
A = {x, x, y}
B = {x, y}
```

An equivalent and more portable formulation is to group by every output column
and compare multiplicities:

```sql
SELECT columns, COUNT(*)
FROM result
GROUP BY columns
```

The grouped representations of the two results must then be compared using
**NULL-safe equality**.

These approaches provide deterministic equality under the comparison semantics of
the DBMS.

**Key references**

- PostgreSQL documentation, *Combining Queries (UNION, INTERSECT, EXCEPT)*.
- Microsoft SQL Server documentation, *Set Operators – EXCEPT and INTERSECT*.
- Oracle Database documentation, *Set Operators*.

---

## 3. Database algorithms underlying exact comparison

Large-scale equality comparison ultimately reduces to the classical database
problem of matching tuples.

The database literature identifies two dominant physical strategies:

- **sorting**, followed by merge comparison;
- **hashing**, followed by equality matching or aggregation.

Graefe's influential survey shows how sorting and hashing underpin joins,
duplicate elimination, grouping and set operations. Hash-based approaches
typically provide expected linear processing behaviour, whereas sorting requires
approximately $O(N \log N)$ comparisons and may require external-memory
processing when datasets exceed RAM.

For very large datasets, both approaches rely on:

- partitioning;
- spilling to disk;
- parallel execution;
- distributed shuffling.

**Key reference**

- Graefe, G. (1993). **Query Evaluation Techniques for Large Databases.** *ACM
  Computing Surveys*, 25(2), 73–170.
  <https://doi.org/10.1145/152610.152611>

This remains a foundational reference for understanding the computational basis of
large-scale result comparison.

---

## 4. Database testing and result-set oracles

A related literature comes from **DBMS testing**, where query results are used as
test oracles.

Differential testing executes equivalent or related queries and compares their
outputs. This literature highlights an important difficulty: apparent differences
may arise from legitimate differences in:

- `NULL` handling;
- implicit type coercion;
- floating-point behaviour;
- string and collation semantics;
- non-deterministic expressions.

Rigger and Su's work on **Pivoted Query Synthesis (PQS)** is particularly relevant
because it discusses the limitations of result-based database test oracles. PQS
itself is not a complete equality algorithm — it focuses on containment rather than
complete bag equality — but the work provides useful context for designing reliable
SQL validation systems.

**Key reference**

- Rigger, M. & Su, Z. (2020). **Testing Database Engines via Pivoted Query
  Synthesis.** *14th USENIX Symposium on Operating Systems Design and
  Implementation (OSDI '20)*.
  <https://www.usenix.org/conference/osdi20/presentation/rigger>

---

## 5. Fingerprints and hashing

For very large datasets, transferring or sorting every row can be expensive. A
common alternative is to compute a compact **fingerprint** of the result.

The theoretical foundation comes from work on **fingerprinting and streaming
algorithms**, where a multiset is represented by a compact algebraic summary.

The important theoretical distinction is:

> A fingerprint mismatch proves that two datasets differ, but matching fixed-size
> fingerprints cannot mathematically prove equality because collisions are
> possible.

Therefore a hash mismatch is conclusive:

$$\text{hash}(A) \neq \text{hash}(B) \Rightarrow A \neq B$$

but a hash match is not:

$$\text{hash}(A) = \text{hash}(B) \not\Rightarrow A = B$$

with absolute certainty.

This distinction is critical when SQL checksums or cryptographic hashes are
proposed as equality tests.

**Key references**

- Rabin, M. O. (1981). **Fingerprinting by Random Polynomials.** Harvard
  University, Center for Research in Computing Technology.
- Cormode, G. & Muthukrishnan, S. (2005). **An Improved Data Stream Summary: The
  Count-Min Sketch and its Applications.** *Journal of Algorithms*, 55(1), 58–75.
- Muthukrishnan, S. (2005). **Data Streams: Algorithms and Applications.**
  *Foundations and Trends in Theoretical Computer Science*, 1(2).

The broader streaming literature provides the theoretical basis for probabilistic
multiset comparison.

---

## 6. Partitioned hashing and Merkle-style comparison

For extremely large datasets, a useful engineering architecture combines
**partitioning and hierarchical fingerprints**:

```text
Dataset A ─┐
           ├─ Partition → fingerprint partitions
Dataset B ─┘
                     ↓
              compare fingerprints
                     ↓
          investigate only mismatches
                     ↓
             exact row comparison
```

Merkle-tree-style structures extend this idea hierarchically. Matching branches
can be skipped, while mismatching branches are recursively subdivided.

Related work on **set reconciliation**, including Invertible Bloom Lookup Tables
(IBLTs), studies how two large collections can efficiently identify relatively
small differences.

**Key reference**

- Goodrich, M. T. & Mitzenmacher, M. (2011). **Invertible Bloom Lookup Tables.**
  *49th Annual Allerton Conference on Communication, Control, and Computing*.
  <https://doi.org/10.1109/Allerton.2011.6120248>

These techniques are particularly attractive when datasets contain billions of
rows but only a small fraction are expected to differ.

However, if matching partitions are accepted solely because their hashes match,
the final equality statement remains **probabilistic**.

---

## 7. Recommended interpretation of the literature

The literature suggests a useful hierarchy:

| Method | Scalability | Equality guarantee |
|--------|-------------|--------------------|
| Bidirectional `EXCEPT ALL` | Medium–high | **Exact** |
| `GROUP BY columns, COUNT(*)` | High | **Exact** |
| Sort + merge comparison | High | **Exact** |
| Partition + exact comparison | Very high | **Exact** |
| Row-level cryptographic hashes | Very high | Probabilistic unless original rows are subsequently compared |
| Aggregate checksum | Very high | Probabilistic, potentially weak |
| Merkle / hierarchical hashing | Very high | Probabilistic unless all relevant leaves receive exact comparison |

The strongest architecture for **strict equality at large scale** is therefore:

> **Schema validation → deterministic partitioning → exact multiset comparison
> within every partition.**

Hashes can be added to accelerate mismatch localisation:

> **Schema validation → canonicalisation → partition fingerprints → hierarchical
> localisation → exact comparison of suspect partitions.**

The second architecture can dramatically reduce I/O when differences are sparse,
but matching hashes alone should not be described as mathematical proof.

---

## How this relates to the Darwin build-speedup gate

The warehouse-speedup correctness gate (page 12) sits deliberately in the
**"exact, aggregate-based"** part of this hierarchy, applied per partition
(table):

- It compares **row counts** and **distinct-key counts** — the multiplicity and
  grain checks of §2's `GROUP BY … COUNT(*)` formulation.
- It compares **rounded column sums** and **date/time ranges** — an
  aggregate/fingerprint summary (§5) that is deliberately **float-tolerant** to
  absorb the last-bit reordering non-determinism §4 warns about.
- It treats each of the five materialised tables as a **partition** (§6),
  fingerprinting them independently.

Per the literature, an aggregate summary alone is *probabilistic* — matching sums
and counts do not, by themselves, constitute a mathematical proof of bag equality.
The gate mitigates this the way §7 recommends: the summary is **narrow and multi-
dimensional** (count + distinct keys + per-column sums + ranges must *all* agree),
which makes an undetected difference require a simultaneous, mutually-cancelling
change across several independent aggregates — vanishingly unlikely for the kinds
of rewrites in scope (added `PRAGMA`s, extra threads, restructured window/scan
passes). For a *proof-grade* guarantee one would add the §2 exact step
(`EXCEPT ALL` / grouped multiset comparison) on any partition whose fingerprint
matches; the report's "byte-identical" claim rests on the strong aggregate
fingerprint plus the fact that every accepted program re-derives it against a
freshly-rebuilt pristine baseline.

---

## Key references

1. **Graefe, G. (1993).** *Query Evaluation Techniques for Large Databases.* ACM
   Computing Surveys, 25(2), 73–170.
   <https://doi.org/10.1145/152610.152611>
2. **Rigger, M. & Su, Z. (2020).** *Testing Database Engines via Pivoted Query
   Synthesis.* OSDI '20.
   <https://www.usenix.org/conference/osdi20/presentation/rigger>
3. **Rabin, M. O. (1981).** *Fingerprinting by Random Polynomials.* Harvard
   University.
4. **Goodrich, M. T. & Mitzenmacher, M. (2011).** *Invertible Bloom Lookup
   Tables.* Allerton Conference.
   <https://doi.org/10.1109/Allerton.2011.6120248>
5. **Muthukrishnan, S. (2005).** *Data Streams: Algorithms and Applications.*
   Foundations and Trends in Theoretical Computer Science.
6. **PostgreSQL Documentation.** *Combining Queries: UNION, INTERSECT and EXCEPT.*
   <https://www.postgresql.org/docs/current/queries-union.html>
7. **Microsoft SQL Server Documentation.** *Set Operators – EXCEPT and INTERSECT.*
   <https://learn.microsoft.com/sql/t-sql/language-elements/set-operators-except-and-intersect-transact-sql>
8. **Oracle Database Documentation.** *Set Operators.*
   <https://docs.oracle.com/en/database/>

**Overall conclusion:** the literature supports treating the problem as **exact
multiset reconciliation**, with classical sort/hash relational algorithms
providing the definitive equality test and fingerprinting/Merkle techniques
serving primarily as scalable acceleration and localisation mechanisms.
