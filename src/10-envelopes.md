# Envelopes

\epigraph{Data are imagined and enunciated against the seamlessness of phenomena.
}{Lisa Gitelman, "Raw Data" is an Oxymoron (2013)}

Envelopes are JSON wrappers that enable sharing transactions incrementally and augmenting them with non-contractual metadata.

Apps MUST normalize a transaction's contract before wrapping it in an envelope (see Normalization).


## Envelope Format

Apps MUST populate and recognize the following envelope fields at minimum:

- `ID`: The transaction's ID, which corresponds to its contract's CID, without a `cid` prefix (`"f01551220ce922..."`).

- `type`: The contract's type, formatted like an HTTP or Email content-type header's value (`"text/markdown; charset=UTF-8; variant=pandoc"`).

- `title` (Optional): The transaction's user-defined title (`"Groceries at Acme ($27.63)"`; see Transaction Titles).

- `units` (Optional): The list unit cluster objects indexed by their canonical ID (`{"f01711220a26cd...": {"USD": 1, "$1": 1, "US$1": 1, ...}, ...}`; see Canonical IDs, Currency Units, and Unit Clusters). Apps MUST append any unit cluster they've matched that lacks a functionally equivalent entry, and MUST leave other entries untouched.

- `references`: The list of transaction docket IDs indexed by the book ID that contains them (`{"909cb...": "f12207e996...", ...}`; see Book IDs and Docket IDs). Apps MUST add or update their docket ID, and MUST leave other entries untouched.

- `signatures` (Optional): The list of signature objects indexed by their canonical ID (`{"f01711220f1a73...": {"signer": "did:key:z6MkCMyGw...", ...}, ...}`; see Signatures and Signature Objects). Apps MUST populate this field with relevant signatures they have for the contract (see Gossip).


### Signature Objects

Apps MUST recognize and populate the following signature object fields (see Signatures):

- `signer`: The signer's key in `did:key` format (`"did:key:z6MkCMyGw..."`).

- `date`: The UTC signing date in ISO 8601 extended format, set on the basis of the signer's wall clock at the time of signing (`"2026-04-10T14:30:00Z"`).

- `signature`: The signature, as a signature in `varsig` format or a file in `cid` format (`"zdpu6vTR4..."`).

- `payload` (Optional): The JSON-formatted payload, if the signature is not for the contract itself (`{"signed": "cid:f01551220ce922..."}`; see Promises and Promise Predicates).

- `authorizations` (Optional): A list of UCAN authorizations, if applicable (`["zdpu6Xm8h...", ...]`; see Authorizations, `did:key` Proofs, Signatures, and Disputes), in lexicographical order.

- `bootstrap` (Optional): The signer's bootstrap handle in URI format (`"p2pledger:de72e..."`; see Bootstrap Handles).

Fields are required unless expressly marked as optional in the above two lists, and apps MUST omit empty fields (`null`, `""`, or `[]`) marked as optional.

Apps MAY recognize more fields at their discretion, but SHOULD namespace them behind a `vendor:<name>:` prefix to avoid collisions until enough vendors agree on the semantics. Heeding this suggestion will help avert the interoperability problems that plagued early internet browsers.


## Unit Clusters

Currency unit clusters allow ledgers to reconcile transactions with different symbols, magnitudes, and formatting conventions for the same underlying unit.

Unit clusters are intended to be something of a Rosetta stone for each currency unit, with a unit's meaning evolving over time, much like the meaning of a word does in a language---and with usage dictating a word's meaning, not the other way around. Unit semantics then emerge organically on the transaction graph as ledgers exchange unit clusters (see Envelopes), without a centralized source of truth.

Apps MUST support a baseline unit cluster functionality for interoperability, and MAY support more sophisticated functionality at their discretion.


### Cluster Format

Apps MAY store unit clusters as they see fit, but MUST accept and share unit clusters in their canonical JSON object format. In this format:

- Keys that correspond to a 3-letter all-caps pattern usually correspond to ISO 4217 codes, and MUST be included as is, without spaces or positional digit indicator (`EUR`).

- Keys of other units must be trimmed, with internal spaces (unicode Z class) normalized to one space, and a `1` as amount position indicator (the position mask) with no space separator between it and the unit (`1€`, `1M€`, `€1`, `€1M`, `1Euro`, `1Euros`, `1M Euros`).

- Keys that correspond to infixed currency symbols MUST also have `0`-padding with no space to indicate the expected decimal precision on the decimal side (`1€00`). Note that different paddings are different entries with different decimal precisions (`0€1 == 0€10`).

- Values MUST be a power-of-10 factors relative to the reference unit(s) whose value is 1, so that `reference_amount = alias_amount × cluster[alias]`.

Example that illustrates all of the above:

    {
      "EUR": 1, "€1": 1, "1€": 1, "1€00": 1,
      "€1M": 1000000, "1M€": 1000000,
      "1Euro": 1, "1Euros": 1,
      "1M Euros": 1000000
    }

Apps MUST require that cluster values are positive or negative integer powers of 10, so end-users don't confuse unit clusters with or abuse them as foreign exchange rates (use Example Transactions for a XAU/USD trade example).

Apps MUST require that at least one cluster key has a value of 1.

Not all languages pluralize words the same way, or all words the same way, or even like Latin-based languages (take Hungarian), so duplicate singular/plural pairs are inevitable---embrace them as data.


### Default Clusters

Apps MUST seed currency unit clusters with their standard (ISO 4217) currency code(s), its local symbol, and the standard international symbol if different from the latter, with appropriate position masks as relevant. The minimum USD, GBP, EUR, CNY, JPY, and INR seeds:

    {"USD": 1, "$1": 1}
    {"GBP": 1, "£1": 1}
    {"EUR": 1, "€1": 1, "1€": 1}
    {"CNY": 1, "1元": 1, "¥1": 1}
    {"JPY": 1, "1円": 1, "¥1": 1}
    {"INR": 1, "₹1": 1}

Apps SHOULD pre-populate common ISO-like, local, and disambiguation symbols, if any, and SHOULD ignore super- and subunits for this purpose unless price tags routinely use them instead of the unit itself. More ideal USD, GBP, EUR, CNY, and JPY seeds, with a few disambiguated symbols, infixed variations, and a few magnitudes thrown in:

    {"USD": 1, "$1": 1, "US$1": 1, "U$1": 1,
      "$1M": 1000000}
    {"GBP": 1, "£1": 1, "£1p00": 1, "1p": 0.01,
      "£1M": 1000000}
    {"EUR": 1, "€1": 1, "1€": 1, "1€00": 1,
      "€1M": 1000000, "1M€": 1000000}
    {"CNY": 1, "RMB": 1, "1元": 1, "¥1": 1, "CN¥1": 1,
      "1万": 10000, "1万元": 10000,
      "1亿": 100000000, "1亿元": 100000000}
    {"JPY": 1, "1円": 1, "¥1": 1, "JP¥1": 1,
      "1万": 10000, "1万円": 10000,
      "1億": 100000000, "1億円": 100000000}
    {"INR": 1, "₹1": 1,
      "₹1L": 100000, "₹1Cr": 10000000}

Apps MAY extend baselines with cryptocurrencies, commodities, or community units at their discretion:

    {"BTC": 1, "₿1": 1, "1₿": 1, "1sat": 0.00000001}
    {"ETH": 1, "Ξ1": 1, "1Gwei": 0.000000001}

These specifications' repository [@P2PLedgersRepo] contains a crowdsourced list of seed clusters.


### Cluster Display

Apps SHOULD default to the first key in the JSON object with a value of 1 and a position mask (`€1` for Euros) as the canonical display unit for UI purposes, or the ISO code as suffix after a space (that is, accounting style `1 USD`) if the unit has no unit with a position mask.

Apps SHOULD provide UI to let users customize how they want the unit displayed. Vendors should mind that end-users might want spaces---consider a "Display As" setting that doesn't limit them to the cluster's keys.

Apps SHOULD ideally derive display preferences from what end-users actually put in contracts.


### Transaction Units

Apps MUST identify units used in a contract before putting it in an envelope, and MUST share the unit clusters they've identified in their canonical JSON dictionary format in the envelopes.

Apps MUST store unit clusters used in transactions separately from those used inside the app itself, and MUST NOT blindly merge new unit cluster entries. This ensures that conflicting semantics inside envelope clusters can exist without affecting the ledgers held by the app.

With this caveat spelt out, some merging MAY be necessary because apps MUST NOT allow gossiping much less signing a transaction with an unknown currency unit.


### Unit Identification

Apps SHOULD support creating or amending unit clusters based on what is used inside transactions.

Apps SHOULD use the unit clusters that the other counterparties attached to the transaction to identify unknown currency units.

Apps SHOULD default to assuming a typo led to the unknown unit if all else fails, since that will usually be the case.

Apps SHOULD provide UI that sets the most likely unit used in a transaction while allowing end-users to override it. One way to do that is to populate a dropdown with the candidates, with the most likely option pre-selected, and final options that enable creating or updating a unit cluster if needed.

Apps SHOULD recognize common magnitude suffixes automatically. Frequently used ones include `M` for million (1,000,000) in European language-based countries, `万` (`만`, in Korea) for myriads (10,000) in East Asia, and `L` and `Cr` for Lakh and Crore (1,00,000 and 1,00,00,000) in South Asia. An unknown `¤1M` or `1L¤` occurrence almost certainly calls for a `¤1M` or a `1L¤` entry in a unit cluster with a `¤1` or `1¤` key respectively.

Apps SHOULD recognize infixed units properly. An amount like `0$01` or `£0p01` SHOULD lead to locating a unit cluster with a `1$00` or `£1p00` entry---and SHOULD prompt a transaction edit or creating the relevant entry in a cluster with a `1$` or `£1p00` entry respectively.

A naive comparison of unit clusters (searching a reference unit in the cluster using case insensitive matching), statistical analysis (`$` probably means USD if ledger transactions typically use that unit), and existing unit clusters in the envelope will usually be enough to identify the units in transactions, so apps MAY stick with that as baseline functionality.

Apps SHOULD more ideally use fuzzy matching (SymSpell, Tantivy, SQLite FTS5, Meilisearch) to match currency units.


### Cluster Amendments

Apps SHOULD try to amend unit clusters based on the clusters being shared in transactions, but MUST be wary of semantic differences while doing so.

A good legal adage to have in mind for this purpose is: one makes a precedent, two makes evidence, and more makes a custom. It is not safe to automatically merge a new key until several counterparties have suggested it repeatedly.

Anything short of this "many said this many times" inference SHOULD require a prompt before merging---or just let it be until it's safe to merge later. Note that this heuristic is different from the way we learn an association. A single occurrence of a new word in a conversation is often enough to grasp its meaning by jumping to conclusions. This requires repeated occurrences, so it's closer to proof through conformity.

Apps SHOULD distinguish between inferred and confirmed keys in unit clusters. A key SHOULD NOT be marked as confirmed unless the key was in the defaults or the end-user actually used it in a transaction.

Apps SHOULD allow users to manually amend unit clusters in case they want to add or remove keys directly.


## Promise Predicates

A promise predicate, or predicate for short, is a flat JSON object whose fields define constraints that MUST all be met. They enable issuing signature promises (see Promises).

Apps SHOULD _always_ issue promises unless the conditions to release the final signature are met already.

### Predicate Types

Apps MUST support the following predicate fields as a baseline:

- `signed` (required), with the transaction's contract's CID as argument. This is the only required field. It ties the payload's signature to the contract and allows automating the due diligence (see Due Diligence). It blocks the final signature for this contract until the issuer holds a final signature or a signature promise for all of the required signers (see Finalization), _and_ holds all of the requisite transaction authorizations, _and_ has verified all of the `did:key` proofs, _and_ can determine from the other predicates that the promised signatures will all be released.

        {"signed": "cid:f01551220ce922..."}

- `deadline`, with a UTC date in ISO 8601 Extended format as argument. This blocks the final signature unless the specified deadline is met according to the issuer's wall clock. Apps SHOULD flag deals that get signed past due for end-user review, since end-users might still want to issue a final signature manually after that.

        {
          "signed": "cid:f01551220ce922...",
          "deadline": "2026-04-10T14:30:00Z"
        }

- `custom`, with a freeform string argument. This blocks the final signature pending a custom requirement that the issuer will need to clear _manually_. This catch-all predicate allows adding off-graph third-party dependencies like regulatory, financing, or investor coalition-related clauses.

        {
          "signed": "cid:f01551220ce922...",
          "custom": "Provided this/that VC also signs."
        }


### Predicate Deadlocks

Promises can produce deadlocks when promises are waiting for one another to clear before releasing their own final signature.

Apps SHOULD flag predicates that are blocking for review by their issuer. This will typically be tied to `custom` predicates: everyone issued a promise, but one or more participant needs to manually clear a deal. No heuristic can hope to automate this. Apps SHOULD flag the blocking promises and offer appropriate UI options ("Remind me in ...") in case the condition is not yet met---or won't ever be.


### Custom Predicates

Apps MUST treat `custom` predicates and unknown predicate fields as _not_ met. That makes them all blocking.

Apps MAY add custom predicate fields at their discretion, but SHOULD namespace them behind a `vendor:<name>:` prefix to avoid collisions until enough vendors agree on the semantics. Heeding this suggestion will help avert the interoperability problems that plagued early internet browsers.

Apps SHOULD avoid using arrays inside predicates and predicates that introduce non-monotonic state. A promise's canonical ID (see Canonical IDs) depends on a consistent serialization, and there can be no guarantee that apps won't change the order of array values---at best these specifications tell apps to not do so and Murphy's Law predicts one app will do it anyway. Non-monotonic states mean a final signature can get released based on assumptions that can't be evaluated in isolation. Compare meeting a deadline according to the signer's wall clock with requiring that a condition is _not_ met, with network latency hiding that it actually just did.

