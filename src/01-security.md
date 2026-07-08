# Security

\epigraph{Privacy is necessary for an open society in the electronic age.
}{Eric Hughes, Cypherpunk's Manifesto (1993)}

An important goal that permeates throughout this document is ensuring that no single party can ever become an all-powerful middleman that controls part or all of the transaction graph.

The threat model assumes adversarial or careless vendors, end-users, apps, and infrastructure, and that transactions around end-users you trust are the only source of trust.


## Encryption

Apps SHOULD use adequate security protocols, and MAY refuse to interact with apps that do not. Cryptography evolves constantly, so specifics beyond what's in these specifications are the vendors' discretion.

Apps MUST expose a public key per ledger they hold to sign transactions (their ledger key, or key for short), and MUST share and update such keys as needed in transactions (see Redlining and Key Rotations). This ensures keys propagate and stay current as apps interact, with each app serving as a local key registry.

Apps MAY store the public keys of ledgers for any duration, and MUST store the ledger keys of ledgers they're gossiping with (see Gossip and Transmissions) until the pending transactions with them are finalized or purged. This ensures apps can gossip about ledgers they don't know or can't reach.


## Forensics

Apps MUST maintain an append-only log for their transaction history. This log MUST compute its next hash based on the data being logged, its previous state, and the local timestamp (see Logging).

This transaction history is not intended to synchronize hashes much less full logs between ledgers, nor is it intended for any type of consensus automation. It does not even try to be those things.

Rather, it is an append-only record of locally timestamped events that arrive asynchronously on disparate devices whose clocks are likely out of sync and possibly tampered with. Anyone using this as forensic evidence SHOULD assume timestamps in this log are dubious. Events could get logged long after they've been sent, so not even local timestamps can be trusted, and no assumption can be made about the event order and hashes across replicas of the same ledger (see Synchronization).

What the log is intended to provide is a tamper-resistant record of the order in which _local_ events containing _non-local_ references get committed to the log. Put another way, ledgers exchange encrypted information about their state as they interact, and embed that information into their own future state. These entangled histories make rewriting a ledger's transaction history impossible without also rewriting that of nearby ledgers on the graph to cover it up.

This tamper-resistant evidence of consideration and intent makes transactions on this graph _far more_ enforceable than they'd be with a mere cryptographic signature, and the dispute resolution process (see Disputes) offers repudiation guarantees in case of private key misuse that a blockchain cannot match without Orwellian levels of control.

Fittingly, this tamper-resistance is socio-cryptographic rather than absolute. Consider a gaslighting attack, where an adversary coordinates rewrites around a node until it abdicates its own judgement to its context. The parallels with conformity and deference to authority are striking [@Asch1956; @Milgram1963]. We'll flesh out the link with cognition later.

These logs enable sequencing events without needing synchronized wall clocks, and defining topologies on the transaction graph. This ties into spacetime and causal set theory, but that discussion will wait too. What matters for our sake is that these logs have strong forensic value.

See Logging for the details on log formats and device synchronization.


## Wall Clocks

The unreliability of wall clocks may need stressing for non-technical readers. Computers use internal oscillators to track time and NTP servers (Network Time Protocol) as their external source of truth. A computer's wall clock could be tampered with, the reference server it's deferring to could be lying, and the routers in between them could be lying too. Adding insult to injury, NTP pools aren't secure, so your choices are trusting a secure but specific NTP provider (plague) or trusting that no one is inside your router (cholera).

Transaction participants set signature deadlines and authorization expirations all the same, so we need to mind wall clocks usage in deadlines and delegated signatures (see Promises and `/sign` Authorizations). Not all wall clock checks are made equal, however, because some transactions are harder to reverse from the perspective of of the graph.

Critical transactions add or revoke proofs, or assign an executable action to _any_ of its signers (see Instructions). The first allows adding or removing a ledger controller. The other, anything a script can do, so could trigger a wire transfer or a cryptocurrency transaction. Given the stakes, a fresh wall clock check when signing or verifying the signature of such transactions makes sense.

Non-critical transactions can be more lenient. Off-graph due diligence is still be warranted before releasing, shipping, or clearing what needs to be, but the tradeoff tilts toward making ledgers work offline since the transaction itself can be disputed as fraudulent and reversed.

See Logging for the details on wall clock synchronization and forensics.


## Identifiers

The takeaways so non-technical readers can skip past the uncharacteristic use of jargon: Use IDs that won't collide, encode them so they play well with all systems, and use self-describing formats---meaning files, keys, and signatures in `cid`, `did:key`, and `varsig` format respectively.

These specifications use collision-resistant IDs, or IDs for short, to mean IDs that were generated using random or hash-based methods that ensure they are adequately collision-resistant.

Apps MAY encode collision-resistant IDs as they see fit when sharing them with other apps, but MUST only share such IDs as filename-, shell-, and URL-safe strings---meaning all characters must be inside the `[a-zA-Z0-9_.-]` alphabet. This ensures `base16`, `base58`, `base58btc`, and other encodings are all fine up to `base64url` with no `=` padding.

These specifications use:

- Content Identifier (CID) of a non-JSON file to mean the ID derived by hashing its byte stream, and augmenting the result so it's in a CIDv1-compatible format [@CID]. Contract attachments are typically terminal leaf node with no outbound links (`raw` multicodec `0x55`).

- Content Identifier (CID) of a JSON file to mean its canonical ID (see below).

- File in `cid` format to mean `cid:<cid>` where `<cid>` is the file's Content Identifier.

- Public key in `did:key` format to mean `did:key:<Key>` where `<Key>` is that public key encoded and augmented as defined by the `did:key` format [@DidKey].

- Signature in `varsig` format to mean a cryptographic signature encoded as a string in `varsig` v1-compatible format [@Varsig].

These self-describing formats [@Multiformats] ensure interoperability with web3 projects like IPFS [@IPFS].

These specifications use shortened IDs in examples for brevity and readability---actual IDs would be longer.


## Canonical IDs

A Canonical ID (CID) is a deterministic content ID for JSON-based data. CIDs enable apps to consistently identify JSON-based data as those get exchanged despite slight inconsistencies tied to asynchronous edits.

Apps MUST support encoding JSON-based data into a CBOR byte stream (RFC 8949) according to the DAG-CBOR Specification [@DagCBOR]. This guarantees a 1:1 mapping between a JSON object's state and a CBOR byte stream by normalizing the order and format of JSON data. Apps SHOULD use an existing DAG-CBOR library for this purpose.

A JSON datum's canonical ID is the content ID of this canonical byte stream. These identifiers get used inside envelopes (see Envelopes), so a consistent canonical ID representation is desirable: apps MUST give this canonical byte stream the `dag-cbor` multicodec (`0x71`).


## Privacy

Apps MUST encrypt any data they hold in storage and in transit. Vendors should use their best judgement on where to draw the line: unencrypted data in RAM is impractical to avoid, but that doesn't make unencrypted data in Memcached okay.

Apps MUST encrypt and sign communications with other apps except as needed to first establish a secure channel (see Transmissions), and MUST flatly deny all other interactions to not leak meta-information.

Apps MUST authenticate ledger controllers (see Authentication) before granting them access to the data the app holds, whether for use inside it, or outside it using transaction protocols (see Gossip and Trust) or other APIs that grant access to that data, nominal or anonymized, as records or aggregates, for any purpose---analysis, audits, reporting, load balancing, anything.

Uncompromising transaction privacy is a simple matter of creating new ledgers. Fill them directly or through intermediaries so they look creditworthy (see Intermediaries), exactly like you'd fill or pay someone to fill a prepaid card. With this said, transactions usually need to be kept confidential rather than made anonymous, and creating a new ledger is overkill in that case.

Transaction confidentiality is a simple matter of having a payment intermediary pay the bill. This guarantees that the Trust protocol, which normally reveals a non-zero balance along with direction and magnitude hints to help consolidate debt loops, leaks nothing---since the intermediary consolidated the transaction at payment time. Apps SHOULD offer UI (a checkbox) to enable ledger controllers to mark some or all transactions as confidential and automate enforcing that an intermediary pay the transaction in full.

Vendors should adopt the mindset that the best way to not leak information---or worse, find it dumped in a data breach---is to not ask for it to begin with. As such, Apps SHOULD NOT require personally identifiable information beyond what's needed for permission control (see Authorizations) and what end-users volunteer inside the transactions themselves.


## Authentication

Conceptually, authentication has two models:

1. Trust on first use, like when someone tells you their name when you first meet, or when you manually trust an SSH host on your first login, or in our case when a ledger's controller might trust another ledger's identity when the two ledgers first interact.

2. Proof, like when someone vouches for you (friends introduce you to someone, trusted peers have signed your public key), or when you show you control known data (a private key, an email, a website, a phone number, a password, a device, a fingerprint, or more, with multi-factor authentication).

Our main concerns are, how can you tell that this ledger with a public key you don't know is not a malicious user, and what to do when end-users rotate keys, lose devices, or simply merge ledgers? Rephrased in real life terms, how would you prove you are you after changing your signature? Essentially, you'd show a paper with your new signature signed using an old signature, or line up people that will vouch it is as evidence. With this context out of the way:

Apps MUST accommodate end-users that create and merge ledgers as they see fit across the transaction graph, and MUST accommodate end-users that lose control of their proof methods. To that end, apps MUST:

1. Use the ledger's current ledger key as its identity in transactions and in the transaction log (see Forensics).

2. Identify ledgers by their identity cluster, which in practical terms means a key can have a parent key, and the identity cluster is the resulting set of related keys.

3. Allow ledgers to sign a new key with an old one as proof that they are the same (see `did:key` Proofs). Keys are unique to a ledger, so this enables merging ledgers.

4. Allow ledgers to associate their key with addresses that they control as API endpoints (url, email, other; see Address Proofs). These addresses MAY be tied to more than one ledger, so apps MUST NOT use them for authentication except locally (like a unique sign-in or recovery link sent to an email).

5. Allow ledgers to permanently repudiate proofs from a specified date. This is about the proof only. Apps MUST dissociate ledgers that got merged after the specified date, and MUST let end-users handle the fallout using disputes.

6. Allow other ledgers to vouch for a ledger, as a trust signal that doubles as a recovery method (see Vouching).

7. Defer to the ledger's controller when a ledger is unknown and trust is low. This is UI-based rather than prompt-based, and trust by trusted peers could tilt things enough to greenlight an unknown ledger (see Trust).

The specifics are at the vendors' discretion, so long as the implementation is compatible with the per-ledger, proof-based authentication approach above. The point is accommodating the instructions used in transactions and the signals needed to assess a ledger's trustworthiness (see Instructions and Trust).

Apps SHOULD NOT gamify vouching for other ledgers. Vouching's principal use is to allow orderly ledger recovery when its controller is unresponsive (see Dead Ledgers). It's the equivalent of giving someone a power of attorney that kicks in when the app determines you're not actively managing your finances yourself.

Beyond this, apps MAY have any number of controllers that manage any number of ledgers. Community-based payment intermediaries, for instance, are multi-user ledgers (see Communities). How this works is at the vendors' discretion, but the parallels between users and ledgers in this section and the next one are transparent enough that treating user and ledger keys the same is recommended. OS-secured private keys protected by passwords and single-use email links as proofs do the trick, with account recovery through vouching as a bonus.

Single-user, single-ledger apps MAY, of course, use their user's key as their ledger's key---they're our equivalent of the sole proprietorship.


## Ledger Recovery

Apps MUST implement a 7-day grace period whereby any proof that has been active for 7 days or more **remains valid** for the duration of the grace period after being invalidated. This enables recovering from scorched-earth scenarios where an attacker who acquires the key rotates it and burns the bridges to lock out the ledger's owner.

Apps MUST broadcast all proof changes to applicable address proofs (typically email or phone notifications) that are active (including those that just got cancelled and remain valid for a grace period) so proof changes don't escape the attention of ledger controllers. Apps MUST include a rescue link in these notifications.

Invoking an invalidated proof using such a rescue link during this grace period MUST transition the ledger into a Disputed state. When in a Disputed state, the app MUST temporarily suspend all proofs added in the past 7 days except the one used with the rescue link, and disallow signing any transaction except the one needed to re-approve or repudiate these proofs.

If all else fails, the Dead Ledger process enables liquidating a locked ledger provided it was part of a community (see Communities). The process mirrors an off-graph inheritance under the supervision of an authority, with the latter holding the authorization needed to transfer the balance.


## Authorizations

Conceptually, authorization is done in two ways:

1. Role-based means your authorization is based on the roles you have. This is weak and prone to abuse because people will assume you're a cop or a doctor if you look or behave like one.

2. Proof-based means your authorization is based on a verifiable proof that can be chained together and traced back to you, like when you sign a power of attorney and the lawyer you gave it to delegates tasks to a junior. Such proofs are exquisitely strong and traceable with cryptographic signatures.

Our concern is how do you get ledgers to sign that a third party may settle a dispute they contest to begin with, or sign an arbitration that might not go in their favor (see Disputes)? Rephrased in real life terms, how do you get someone to sign something they don't consent to? Essentially, you get them to sign before things turn sour. Contracts typically include a governing law and jurisdiction for that reason. Because ledger transactions require a signature to become triple-entry bookkeeping entries [@Grigg2005], we need an explicit chain of proof---and a potentially irrevocable one at that. With this context in mind:

Apps MUST accommodate proof-based authorizations for ledgers in User Controlled Authorization Networks (UCAN; @UCAN) compatible formats for interoperability. These specifications define authorization capabilities as they become needed---others are at the vendors' discretion.

Beyond this, apps MAY let end-users delegate part or all of their control over ledgers to others at their discretion, conditional or not, revocable or not, and governed at their leisure (see Communities). This ensures parents, tutors, organizations, community members, and others can place checks on what goes onto their balance sheet. How this works is at the vendors' discretion, with a UCAN based approach recommended. The only constraint is that:

Apps MUST issue and MUST accept only transaction signatures that are valid from the ledger's point of view. In other words, apps must use the ledger's key to sign transactions directly, or to sign UCAN authorizations so delegated keys can sign transactions on its behalf. Apps MUST attach UCAN authorizations for delegated signatures to be valid.

This constraint is a very deliberate design choice to ensure authorizations get managed upstream of transactions. It means a structurally invalid authorization issued by an app _can_ yield a valid signed transaction, much like an employee _can_ sign an invalid yet enforceable deal for their organization. Such invalid transactions must go through the normal dispute resolution process if rebuffed.

Single-user, single-ledger apps MAY, as noted earlier, use their user's key as their ledger's key.

Apps SHOULD re-authenticate end-users before letting them sign transactions or do other log-worthy activities if their ongoing session has been inactive, and MUST re-check their authorization to sign transactions before letting them do so.


## Block Lists

Block lists are intended to ensure end-users can police abuse but carry a very real risk of Sybil attacks (like smear campaigns in real life). The onus is on apps and end-users to not let blocks become vectors for censorship.

Apps SHOULD allow ledger controllers to block interacting with any ledger, for any reason or duration.

Apps MAY configure block lists by default, but MUST offer a way to opt out of blocks it enforces by default so end-users can freely opt in or out of them.

Apps SHOULD warn before blocking ledgers they have a balance with. Such blocks mean a creditor throws the towel on a debtor, or a debtor tells a creditor to get lost. Both affect claims and reputation, so could trigger a dispute (see Trust and Disputes).

Apps that allow blacklists SHOULD allow whitelists to override blacklist-level blocks, and SHOULD automatically whitelist all past transaction counterparties that a ledger's controller has not explicitly blocked. This is so ledgers that interact with one another don't inadvertently block one another.


## Transparency

Apps SHOULD be open-source and have a reproducible build process. The latter means the build process should always produces the exact same binary, despite temporary files or random values set at compile time and the like. This is so ledger controllers can check that their app is not malware or spyware.

The spyware angle may need expanding on. Dystopian amounts of trackers exist online (usage trackers, advertisements), offline (surveillance cameras, smart billboards), and at their intersection (bank cards, location pings, social media, chat bots). Those data later go into marketing (ad bidding, customer profiling), security (fraud or other misuse detection), or reporting (fancy charts) tools---or more recently, in systems that deliver humanless analyses, decisions, pre-crime alerts [@Hung2023], kill targets [@King2024], and other hellish slop. This is not preordained. It's the product of choices, and the principal one is engineers enabling jerks who nag for sex or just take it.

In that light, apps SHOULD assume no end-user wants their tracking, SHOULD NOT prompt end-users to opt in on first use, and SHOULD keep all diagnostics logs local until an end-user agrees to send relevant data after a crash.

Vendors should get into 30-minute calls with a half-dozen end-users every now and then instead. Ask what they use your app for, how they use it, and where it gets in their way. A half dozen is a sweet spot that will surface most issues. You'll get far more actionable information about your app and market than from tracking data. Then follow up. A delighted end-user sends referrals like their life depends on it.
