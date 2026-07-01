# Signatures

\epigraph{Equity looks at the intent not at the form.
}{Richard Francis, Maxims of Equity (1728)}

Cryptographically signing a contract is the digital equivalent of putting a wet ink signature on an offline contract---and as with offline contracts, there is more to closing a digital deal than just signing. All manners of due diligence steps are in order, and many contracts don't jump to finalization anyway. It is customary, for instance, to extend an offer that is valid by some date with an implicit signature promise, and many deals, like real estate, involve a signed intent before closing. These specifications reflect this reality by separating signature promises from final signatures.


## Promises

Promises are automated sub-contracts that enable participants to withhold their final signature for a contract until specific conditions are met. They automate the due diligence on the current transaction, and enable setting a deadline so transaction issuers are not extending contracts that are indefinitely valid.

Promises mirror signed intents. They work by signing a predicate instead of the contract itself, and passing that as the signature's payload in the transaction Envelope (see Envelopes). What matters for our immediate purpose is that there are three user-facing predicate types:

- The `signed` predicate enables automating due diligence like a no-nonsense compliance officer would before releasing the final signature.

- The `deadline` predicate enables withholding a final signature if a deadline based on the issuer's wall clock is not met (see Wall Clocks).

- The `custom` predicate enables withholding a final signature until a custom condition is met. Typically, this is for off-graph third-party dependencies like regulatory or financing approvals, or investor coalitions.

Typically, apps will try to issue a signature promise predicated on `signed`, optionally combined with the other two predicates, to automate due diligence (check signatures, proofs, and so forth), and release a final signature only when everything checks out.


### Revoked Promises

Apps MUST allow end-users to revoke a promise that hasn't yet triggered. More often than not, this will be because a `deadline` or a `custom` predicate can no longer be met. Other times, discussions might have dragged on for too long or material adverse changes got in the way. Whatever the reason, a promise's issuer could change their mind.

With this spelt out, promises are not to be issued or revoked lightly. They are "instinct with an obligation," to borrow Justice Benjamin N. Cardozo's formula, and every bit as enforceable as final signatures are. To wit, the contract they refer to includes the `/sign` authorizations needed for any of the participants that signed the transaction to file _and enforce_ a dispute against any of the others that also did (see Disputes and `/sign` authorizations). The others who did not yet sign are shielded (and exempt from) that process. 


## Due Diligence

All sorts of verifications and formalities are needed before and after signing a contract---many can be automated, but not all.

As a rule of thumb, apps MUST NOT release a final signature for contracts it flags during due diligence.


### Parse Errors

Apps MUST NOT allow signing a contract that they cannot parse in full, without errors. Anything short of atomicity on this point would be undefined behavior.

The instruction syntax is extremely forgiving (see Parsing), but Murphy's Law dictates that an avoidable error will arise anyway. Apps SHOULD be helpful---for instance, by feeding instruction subjects and objects through SymSpell to detect typos.


### Malicious Contracts

Apps SHOULD try to warn end-users about malicious transactions they're about to sign. It's possible to dispute them in principle (see Disputes), but reversing an off-graph wire transfer is more involving than repudiating ledger entries, so they're best caught beforehand.

Malicious contracts could come in a rich variety of flavors, so this subsection cannot possibly do the topic justice, but there are a few obvious ones to look out for.

The most important one to look for is instruction injection. Seasoned web app engineers will remember the heydays of header injections. This is the same with ledger entries. Instruction parsing rules (see Parsing) were very deliberately designed to prevent them, but triggers mean they cannot be ruled out entirely.

One prevention strategy is of course to warn aspiring trigger developers about creating transactions without sanitizing input data. Apps SHOULD warn about the issue in their API docs. Ideally give an example of a trigger that consumes a parameter with a colon and ends up creating ledger entries in the customer's favor (cue `customer="Customer: Vendor 100 USD;"`).

Warning end-users that instruction injection can happen is not actionable, and will get ignored eventually---who even reads those asinine certificate-related warnings in browsers?

A better prevention strategy is simply UI-based: apps SHOULD parse instructions automatically and spell out what end-users are committing to before signing. If the participants are happy with a trigger receiving `customer="Customer: Vendor 100 USD;"` or something equally sketchy, then by all means let them.

Beyond that, apps SHOULD flag mixed-script homoglyphs subjects (e.g. Cyrillic characters mixed in with Latin ones), to limit "look-alike" subject attacks in case a victim doesn't pick up on the low trust signals a phishing attempt would have anyway (see Trust).

Apps SHOULD also flag suspicious amounts of spaces (the whole unicode class Z), tabs, and line endings, in case a prankster tried to hide legal fine print or instructions behind scroll bars.

Next, apps MUST flag incoming gossip (see Gossip) that delivers a contract with the `_` template variable (see Templates) still in place and an optional signer (see Optional Signers) for end-user review. The charitable explanations will be that the optional signer's app is buggy or a non-ASCII whitespace character got inserted during a copy and paste operation. The less charitable one is that the signer is trying to get a free a membership or something to that effect.

Lastly, apps MAY have an LLM surface sketchy legal clauses in contracts. Apps SHOULD use a local LLM for this so ledgers don't get monitored through backdoor channels, and SHOULD raise that LLMs can be misleading [@Shapira2026; @Ren2026; @Magesh2024].


### Proof Verifications

As noted earlier, apps SHOULD try to issue a signature promise predicated on `signed` for all transactions, and release a final signature only when the due diligence checks out. That predicate verifies that:

1. All of the requisite signatures are included and valid.

2. All of the requisite authorizations are included and valid.

3. All of the `did:key` proofs inside the contract are valid.

Apps SHOULD flag `/sign` authorizations tied to arbitral authority grants with usual conditions (see Disputes), and SHOULD offer UI that makes the conditions of all such authorizations clear before signing.

The generic `custom` predicate type can be used to withhold the final signature until extra steps are manually marked as completed.

Apps MAY use custom predicate types to add industry-specific steps that can be automated (see Custom Predicates).

Apps SHOULD verify all address proofs in transactions, but SHOULD NOT send the requisite verification requests until after signing the transaction---waiting until then minimizes the probability of input errors like typos.


## Tacit Consent

Tacit consent is what happens when you acquiesce to something through silence or inaction. A useful mnemonic for the different types of legal consent is sex: you can consent or refuse expressly, consent tacitly (go along with the flow, without protesting), or negotiate (ask for money)---on top of the usual legal capacity (old enough, not drunk, not under duress).

Most off-graph obligations arise from tacit consent. No one gives their express consent to being governed, yet they behave like they tacitly consent to it. No parent expressly consented to giving their kids presents on specific dates, yet customs like Christmas obligate them all the same. No one expressly signed up to behave consistently, yet we all instinctively do so and mistrust those that don't. No one expressly signed up to adopt stereotypical behavior, yet we all expect it from others as a mental heuristic. Tacit obligations are _everywhere_ around us.

Tacit consent cannot exist on this transaction graph the way it does off-graph, since cryptographic signatures mean consent is always express. What apps _can_ do instead is offer heuristics. The fuzzy line around "not yet promised" could signal silent refusal, pending consent, or undecided. Apps can make it _less_ blurry by upgrading tacit consent into express consent automatically.

The offline legal record tied to tacit consent gives insights into when signing a contract automatically becomes reasonable. Contracts that saddle you with an obligation are non-starters. It is not okay to send random people your product with a note that says they must pay you if they don't return it, for instance. But the fine line is subtler: the _net_ obligation is what matters in practice. When you issue a bearer IOU, you tacitly consent to pay back the new bearer as the IOU circulates. Similarly, you tacitly consent to pay your mortgage even as the latter gets securitized and resold on Wall Street---your obligation did not change. With this context in mind:

Apps SHOULD automatically issue a final signature for transactions that pass due diligence and do not saddle them with any _net_ obligation. That means the transactions that a) are neutral or positive overall for their ledger balance, b) do not contain legalese or attachments, since those might contain off-graph obligations, and c) only involve trusted counterparties (see Tacit Trust).

This ensures that, given trusted counterparties and no legalese or attachments, participants automatically sign transactions that:

- Are a consolidation or a net donation (see Consolidations).

- Only assigns them a noop action (witnesses in automated transactions).


## Finalization

A transaction becomes finalized when _any_ of the participants holds the final signature of _all_ of its required participants, with the latter meaning all of the ledgers with an action assigned to them (see Actions)---whether bookkeeping lines, executive actions, or noop actions.

This means a participant might not yet know about obligations they've committed to. This mirrors offline businesses whose sales haven't yet reported new deals. Gossip ensures the required signers will all receive the finalized transaction, and in normal circumstances (no repeated timeouts) won't stop until they all do (see Gossip).

Ledgers MAY sign transactions that don't assign them any action (see Optional Signers). This enables community organizers to start and eventually close and tally a poll by signing, and the members to receive the voting tool by signing (see Communities):

    @! Members: > Members
    @! Organizer: poll.wasm
    @! *: vote.wasm

A transaction's date is the earliest date when it became finalized based on the included signatures. One caveat is that wall clocks can be off by a mile in the past or in the future (see Wall Clocks). Transaction logs can settle the matter in case such trifles are contentious (see Forensics).


## Signature Computation

Apps MUST hash signature payloads before signing them, and MAY use the hash and signature algorithms of their choice while doing so (see Encryption), but MUST output signatures as signatures in `varsig` format or files in `cid` format (see Identities).

Apps MUST normalize text-based payloads like contracts before hashing them (see Normalization).

Apps MUST encode JSON-based payloads like promises into a CBOR byte stream (RFC 8949) according to the DAG-CBOR Specification [@DagCBOR], and hash the CBOR byte stream instead of the JSON data. In other words, this is like computing a canonical ID (see Canonical IDs).

Apps MUST hash the raw bytes of other types of payloads. In particular, apps MUST extract the raw bytes from the key in `did:key` format, and hash those only, rather than its string representation.

Apps MUST sign the payload's _raw_ hash digest, not its multiformat augmented version or the latter's string representation.

This ensures a contract, a promise, or a key in `did:key` format produces the same signature across apps.


## UCAN Payloads

Apps MUST support UCAN 1.0 compatible authorizations [@UCAN]. This subsection is a brief primer on how they get signed and how they work.

UCAN authorizations have a three-part envelope (`header.content.signature`) whose content part must be normalized per UCAN specifications before hashing and signing, and whose three-part envelope is serialized to a binary format.

An authorization's content part is a JSON object that lists who is delegating power (`iss`, for issuer), who it's being delegated to (`aud`, for audience), who its principal owner is (`sub`, for subject), and fields to express what is being granted (`cmd`, for command) and under what conditions, plus a few other fields to capture context during invocation. Delegation and invocation payload gets enveloped with a version tag to freeze the semantics.

Signing a UCAN payload means signing its `SigPayload`. Briefly, the token map gets normalized and encoded to a byte stream to ensure these details are in a consistent order [@DagCBOR], and wrapped with the signature algorithm metadata inside a `SigPayload` map. That payload gets hashed and signed like a normal payload, and then wrapped with that signature in a final envelope, which then gets serialized and encoded as a signature in `varsig` format for compactness. Several libraries will do this automatically, including some maintained by the UCAN working group itself.

One of UCAN's most interesting features is that authorizations can be chained. The `SigPayload` map's hash gets augmented with multiformat headers to get the authorization's CID (see Identifiers), and those get used inside proof fields (`prf`). The latter contain the array of CIDs of their authorization's parent tokens, such that the audience (`aud`) of one matches the issuer (`iss`) of the next, and the validity conditions on one allow delegating to the next, so as to verify that chain of issuers all have the power to grant what they claim to be delegating. This enables creating tamper-resistant permission tokens that can be chained securely.

UCAN authorizations are stateless. Their form is verified (is it syntactically correct and signed?), then their substance (is invoking it valid at this time with this data?), in such a way that they're self-contained and invariant. The invoked service might reject the authorization as already used, or revoked, or other internal reasons that external parties cannot see, but the authorization itself is unequivocally valid or not valid.

UCAN capabilities are additive, if with gotchas. Capabilities are union-based: you can grant `/foo/bar` and `/foo/baz` separately to grant both. Satisfying them is not: having the two separately won't let you run compound commands that require both. Nor is locating them: you can't hand your authorizations and let the UCAN library figure out which to use like an OS does with a keychain.

UCAN offers built-in fields to express conditions:

- `nonce` is for replay protection. Set it to a random value for single-use authorizations, or to `null` for multi-use ones.

- `nbf` and `exp` (for not before and expires at) enable setting time bounds, and `iat` (for invoked at) captures the invocation time. `iat` is intended for information only, and SHOULD be taken with a grain of salt since clocks can be tampered with (see Wall Clocks). Apps MUST use the local wall clock in addition to the `iat` field when first verifying an authorization's validity---the `iat` value can be trusted from that point forward.

- `pol` (for policies at delegation) enables shaping what `args` (for arguments at invocation) must be like before passing them to `cmd` at invocation. Proof chains propagate these syntactic-level `pol` constraints downstream. The two are intended for distributed remote procedure calls, and that only.

- `meta` allows signing predefined values, and thereby expressing attenuations and complex constraints that proofs can't just propagate downstream. These constraints MUST be validated at the app-level before execution, and SHOULD get validated when authorizations get shared as well.

The UCAN specifications recommend tolerating a margin of error to account for network delay and clock skew when checking time-sensitive fields like `exp` or `nbf`. Apps SHOULD tolerate 60 seconds in either direction, to align this with wall clock checks (see Wall Clocks).

When verifying proofs (see Due Diligence), apps MUST treat syntactically valid authorizations with unknown `cmd` values as valid but unknown. When used, apps MUST reject them as invalid and unknown.

Apps MAY add authorizations with `cmd` values as they see fit, but SHOULD namespace them behind a `/vendor/<name>/` prefix, to avoid collisions until enough vendors agree on the semantics.

Apps MUST reject authorizations with a supported `cmd` but containing unknown `pol`, `args`, or `meta` keys as invalid.


## `/sign` Authorizations

`/sign` authorizations grant, as the name implies, signing permissions to other keys. They're critical off-graph and on-graph (see Disputes and Vouching), so need fleshing out for interoperability.

The fact that authorizations are stateless is worth stressing, because N-of-M signers and expense caps are common requirements in organizations. There is no re-evaluating John's signature after Jack signs too or because his subordinate Jane just blew his monthly expense cap. From the viewpoint of counterparties, a transaction is signed if the ledger key signed it, and all the proof they need is self-contained inside the authorization chain (see Authorizations and UCAN Payloads). Plus, leaking internal signing rituals is seldom desirable anyway. Any process more complex than a direct signature is better managed by creating a single-use authorization gated on that specific transaction for a single-use key, and releasing their signatures after closing that deal internally.

Internal processes are such a Pandora's Box that `/sign` authorizations don't even try to entertain them, in fact. Their intended use-cases are internal to these specifications:

1. Authorizations gated on `transaction` per above, to keep internal processes off the transaction graph, and to accommodate signing hardware.

2. Authorizations gated on `claim` and `appeals` to set up a state-machine with checks and balances for the dispute process (see Disputes), so arbitrations can be signed on behalf of reluctant participants.

3. Authorizations gated on `inactivity` for ledger recovery.

Apps MUST support signing transactions using UCAN authorizations with a `/sign` command (`cmd`), with the following scopes:

- `/sign`: Grants signing anything for the issuer. Gate on `transaction` to prevent abuses.

- `/sign/contract`: Grants signing transactions that don't add or revoke proofs or assign executables to the issuer. Gate on `transaction` to prevent abuses, and on `claim` and `appeals` for disputes.

- `/sign/recover`: Grants adding proofs for the issuer. Gate on `inactivity` to prevent abuses.

Typically, `/sign` authorizations get used while logged in, so many apps will only ever evaluate delegations ahead of handling signing internally. Apps MAY support `/sign` authorization invocations in APIs, with the following `args`:

- `transaction` (optional, string): Must be a transaction ID, which corresponds to its contract's CID (see Identifiers). Instructs the app to sign the specified transaction and requisite authorizations. Apps MUST NOT gate the `transaction` using `pol`, and MUST reject authorizations that try as invalid, since doing so would neuter dispute related authorizations used in authorization proof chains. Use the `transaction` `meta` gate instead.

Apps MUST support gating `/sign` authorizations using `meta` key-value pairs, with the following semantics:

- `transaction` (optional, string): Must be a transaction ID. The authorization is valid to sign the specified transaction and requisite authorizations only. When evaluating proof chains, apps MUST verify that this gate was passed on as is OR as a `claim` gate with the same value, to ensure single-use keys can grant arbitral authorities.

- `claim` (optional, string): Must be a transaction ID. Required when `appeals` is set. The authorization is valid if and only if all of the required signers (see Finalization) that signed the specified transaction are required signers for this transaction. Note that the specified transaction does **not** need to be finalized (see Revoked Promises): if only two of three required signers signed, for instance, only those two are needed for this authorization to be valid. See `appeals` for how to evaluate this gate in proof chains, see below for how to configure it inside contracts, and see Disputes for how to use it.

- `appeals` (optional, integer): Must be a positive integer, or zero. Required when `claim` is set. When non-zero, the authorization is valid if and only if the holder grants arbitral authority to a key that is not listed among the issuers in the authorization's proof chain. When zero, the holder's decision is final so the holder MUST NOT grant any arbitral authority. When evaluating proof chains, apps MUST verify that the `claim` gate was passed on as is if the `appeals` gate was not changed, or decremented by exactly one otherwise.

- `inactivity` (optional, integer): Must be strictly positive integer. Invalid unless `cmd` is `/sign/recover`. The authorization is valid if and only if the ledger's last `sign-in` event was logged `inactivity` days or more ago, with a day meaning a 86,400-second interval for simplicity. When evaluating proof chains, apps MUST verify that this gate is set to the exact same value.

Apps MUST grant a `/sign/contract` authorization with a `claim` gate set on the current transaction's ID when participants grant an arbitral authority in a contract (see `did:key` Proofs). Apps MUST default `appeals` to a value of `1` for the initial grant unless participants override that default, and MUST allow participants use a Proof argument (`<*:.$appeals=2>`, see Proofs) to override that default. Apps MUST ensure the `appeals` counter got decremented by 1 and that the `transaction` gate got reset when the signer is using their grant to sign the transaction on behalf of others (see Envelopes).

The purpose of such grants is to enable an arbitral authority to sign on behalf of participants, so they all have a valid triple-entry bookkeeping even when a participant is uncooperative. Apps MUST see to it that such grants are useful. Apps MUST reset all gates in new grants other than `claim` and `appeals`, and MUST treat `claim` gated authorizations that try to smuggle any gate other than `claim`, `appeals`, or `transaction` (MUST NOT be set initially, but MAY get set by the holder later) as invalid. In particular, `exp` and `nonce` MUST both be `null`, `nbf` MUST NOT set, `pol` MUST be empty, `iss` MUST be the granter (the ledger key, or the grantee when delegating further), `aud` MUST be the grantee, and `sub` MUST be the ledger key).

Arbitral authority related authorizations don't even try to set time limits, because legal deadlines are social. Statutes of limitations that are impossible to capture might be customary, participants routinely ask for extensions that may or may not get granted, arbitrators don't all enforce deadlines the same way, and people take vacations. Supporting this at the protocol level is as alluring as kicking a hornet's nest. Plus, letting arbitrators set deadlines and judge if they're met is far more fitting: disputes are the _only_ times in this protocol where decisions about you might get made without your consent.

Apps SHOULD provide UI to automatically create `/sign/recover` authorizations for vouching purposes (see Vouching).


## Signing Hardware

Cryptocurrencies have fueled the rise of a signing hardware industry in recent years because cryptocurrency transactions are often non-repudiable---that is, you can't dispute a transaction if a hacker finds your private key and empties your crypto wallet. Peer-to-peer ledgers are blessed with dispute resolution, so that problem doesn't apply to this protocol. Vendors and end-users may want to use signing hardware anyway, for two-factor authentication and for signing transactions especially.

The four key technologies to be aware of are:

- JCS (JSON Canonicalization Scheme, RFC 8785)

- CDDL (Concise Data Definition Language, RFC 8610)

- CBOR (Concise Binary Object Representation, RFC 8949)

- COSE (CBOR Object Signing and Encryption, RFC 9052)

In short, unsorted JSON gets turned into a sorted and more compact CBOR package that must then be wrapped in a COSE envelope so signing hardware can process it. But the transaction format in these specifications sidesteps JSON, so most of what you'll read about these topics will be irrelevant.

In practice, signing hardware only needs to know what payload to sign and what key to use. Some accept an optional string for UI, but not all, and not always the same key. Apps should use the transaction title (see Transaction Titles), if any.

Do _not_ send the contract envelope as is or the requisite contract CID and the authorizations one by one. Sending the first is invalid since you want to sign the contract's CID, and signing payloads one by one sucks with hardware as much as it does with a pen at a law office. For better UI/UX, have the end-user sign once and let the app deal with that grueling mess. The hardware will hold the ledger key or another key with a `/sign` authorization for it. Have it sign a `/sign` authorization gated on that `transaction` for a single-use key. Then, sign the payloads using that key, and slip the authorization into the envelope.

For the rest, you'll typically want to send the signing hardware a `COSE_Sign1` object to collect one signature on the payload.


## Signature Verification

Apps MUST verify signatures by independently recomputing the payload hash and validating the cryptographic proof against the signer's public key. In other words, apps:

1. MUST extract the raw bytes and the algorithm identifier from the signature's self-describing `varsig` or `cid` container---algorithm derivation MUST NOT be assumed or negotiated.

2. MUST use that information to reconstruct the hashed payload that was signed.

3. MUST pass the signer's public key, the raw signature bytes, and the locally computed hash digest to the verification routine to validate the signature.


### Invalid Signatures

Apps MUST treat signatures that use unsupported protocols as invalid, MAY treat signatures that use protocols they deem inadequate as invalid (see Cryptography), MUST treat signatures signed using repudiated ledger keys as invalid (see Key Rotations), and MUST reject invalid signatures.

Apps MUST flag rejected signatures for review. Automations are tricky because end-users will likely want to investigate why a `did:key` proof failed, or want to manually treat a signature rejected on the basis of its protocol as valid because gossip delivered the finalized contract despite this, or want to open a dispute about such transactions, etc. There is no correct way to handle every possible case, so manual review is paramount. Apps MAY, of course, try automate how to process rejected signature anyway, but MUST keep ledger controllers in the loop.

Apps MUST flag transactions whose envelope contains signatures rejected on the basis of the protocol or an old key for review in case the ledger controller wants to accept them anyway (see Invalid Gossip).
