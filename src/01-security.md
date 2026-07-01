# Security

\epigraph{Privacy is necessary for an open society in the electronic age.
}{Eric Hughes, Cypherpunk's Manifesto (1993)}

An important goal that permeates throughout this document, in fact, is ensuring that no single party can become an all-powerful middleman that controls part or all of the transaction graph. The threat model assumes adversarial or careless vendors, end-users, and infrastructure, and that transactions around end-users you trust are the only source of trust.


## Encryption

Apps SHOULD use adequate security protocols, and MAY refuse to interact with apps that do not. Cryptography evolves constantly, so specifics beyond what's in these specifications are the vendors' discretion.

Apps MUST expose a public key per ledger they hold to sign transactions (their ledger key, or key for short), and MUST share and update such keys as needed in transactions (see Redlining and Key Rotations). This ensures keys propagate and stay current as apps interact, with each app serving as a local key registry.

Apps MAY store the public keys of ledgers for any duration, and MUST store the ledger keys of ledgers they're gossiping with (see Gossip) until the pending transactions with them are finalized or purged. This ensures apps can gossip about ledgers they don't yet know or can't reach.


## Identifiers

The takeaways so non-technical readers can skip past the uncharacteristic use of jargon: Use IDs that won't collide, encode them so they play well with all systems, and use self-describing formats---meaning files, keys, and signatures in `cid`, `did:key`, and `varsig` format respectively.

These specifications use collision-resistant IDs, or IDs for short, to mean IDs that were generated using random or hash-based methods that ensure they are adequately collision-resistant.

Apps MAY encode collision-resistant IDs as they see fit when sharing them with other apps, but MUST only share such IDs as filename-, shell-, and URL-safe strings---meaning all characters must be inside the `[a-zA-Z0-9_.-]` alphabet. This ensures `base16`, `base58`, `base58btc`, and other encodings are all fine up to `base64url` with no `=` padding.

These specifications use:

- Content Identifier (CID) to mean the ID derived by hashing the byte stream of the file it refers to and augmenting the result so it's in a CIDv1-compatible format [@CID].

- File in `cid` format to mean `cid:<cid>` where `<cid>` is the file's Content Identifier.

- Public key in `did:key` format to mean `did:key:<Key>` where `<Key>` is that public key encoded and augmented as defined by the `did:key` format [@DidKey].

- Signature in `varsig` format to mean a cryptographic signature encoded as a string in `varsig` v1-compatible format [@Varsig].

These self-describing formats [@Multiformats] ensure interoperability with web3 projects like IPFS [@IPFS].

These specifications use shortened IDs in examples for brevity and readability---actual IDs would be longer.


### Canonical IDs

Canonical IDs are deterministic content IDs for JSON-based data. They enable apps to consistently identify JSON-based data as those get exchanged despite slight inconsistencies tied to asynchronous edits.

Apps MUST support encoding JSON-based data into a CBOR byte stream (RFC 8949) after normalizing it according to the DAG-CBOR Specification [@DagCBOR]. This guarantees a 1:1 mapping between a JSON object's state and a CBOR byte stream by normalizing the order and format of JSON data. Apps SHOULD use an existing DAG-CBOR library for this purpose.

A JSON datum's canonical ID is the content ID of this canonical byte stream. These identifiers get used inside envelopes (see Envelopes), so a consistent canonical ID representation is desirable: apps MUST hash this canonical byte stream using SHA-256 (`0x12`), assign it the `dag-cbor` multicodec (`0x71`), and base16-encode it (`0x66`). This guarantees apps all produce canonical IDs that start with `f01711220`.


### Book IDs

Book IDs enable synchronizing ledgers between devices and hosting many ledgers on the same device without leaking information about these devices or ledgers.

Apps MUST generate a collision-resistant Book ID for each ledger on the device the app is on. Book IDs are intended as anonymized `(device, ledger)` pairs to identify a specific ledger on a specific device, so MUST NOT be derivable from the device's hardware identifiers, secrets, or the ledger's public key.

Apps SHOULD NOT allow regenerating book IDs. The tradeoff of keeping the book ID invariant is a minor metadata leak: over time, regular counterparties will deduce how many devices a ledger is on. The alternative is tracking rolling book lineages and their associated permissions.


### Fingerprints

Fingerprints are relationally salted tokens designed to identify payloads sent by known counterparties without revealing their ledger key to observers.

Conceptually, fingerprints are like Truncated Key Identifiers, with the twists that the payload is based on the public key pair and the transmission channel that ledgers are interacting on instead of one key, and the hash algorithm is derived from the recipient's public key.

To compute a recipient's fingerprint, a sender's app MUST compute:

    Hash(<RecipientKey> || Hash(<SenderKey> || Hash(<RecipientAddress>)))

Where:

1. `<RecipientKey>` and `<SenderKey>` are the recipient's and the sender's raw public key bytes without Multicodec prefixes.

2. `<RecipientAddress>` means the recipient's address scheme and locator exactly like the recipient shared them with the sender, as raw UTF-8 bytes (in other words, preserve the case, and ignore address proof arguments; see Bootstrap Tokens and Address Proofs).

3. `||` means concatenating raw bytes as is.

4. Hash is an algorithm derived from the recipient's public key (see below).

Apps MUST precompute, store, and index the first four bytes (leftmost) of all counterparty fingerprints for fast look-up. Four bytes are enough to guarantee that few if any collisions inside a set will exist, and allow an index layout optimization in database engines that offer Hash indexes.

Apps with enough counterparties that collisions become a problem MAY store more bytes, but SHOULD NOT store the full fingerprint to not invite data breaches as a quick way to build a rainbow table.

Fingerprints allow an encrypted payload's recipient to determine its sender without trying every public key until they find one that works (see Payload Format), and enable ledgers to ask each other about the creditworthiness of a ledger without revealing its identity to those who don't know it (see Trust). In both cases, a simple look-up reduces the search space to a set small enough (typically one candidate key, rarely more) that recomputing the hash of each candidate key is perfectly acceptable.

Apps MUST compute new fingerprints when they learn about new or rotated keys.

Apps MUST temporarily retain old hashes when rotating keys (see Key Rotations), and MUST compute each counterparty's new fingerprint _before_ letting them know about the key rotation.

Cryptography evolves quickly, and setting a hashing algorithm in stone forever would be uncharacteristic of these specifications. Apps MUST decide which hash algorithm to use based on the public key's Multicodec value. _Vendors_ SHOULD exchange and allow a consensus to emerge about what hashing algorithm a given codec gets tied to as they get released. The important factors are security, speed, and hardware availability---good picks are widely available and won't drain phone batteries flat. Vendors SHOULD crowdsource these codec mappings on these specifications' repository [@P2PLedgersRepo]---and SHOULD set up a new repository if its maintainers become compromised or unresponsive.

In the interest of setting a baseline: at the time of writing, apps MUST use Blake3 for curves that are commonly used nowadays, and MUST use SHA3-256 for the post-quantum curves that are emerging. Apps SHOULD NOT allow using curves that don't yet have a vendor-agreed-upon Multicodec mapping, since that would prevent apps from different vendors from being able to interact.


## Secure Channels

Apps MUST treat all channels as insecure for Gossip and Trust purposes---even HTTPS. TLS (RFC 8446) is the only practical option to create secure channels inside browsers, on corporate networks, or on captive portal WiFi networks. It provides strong security, but it uses centralized certificate authorities that could be compromised. Using EDHOC (RFC 9528) would make sense in the scenarios where it works, but the maintenance burden of offering it for those does not. Using TLS for other purposes (see Wall Clocks) is a necessary compromise.

Apps MUST use HPKE (RFC 9180) to seal messages for the recipient's ledger key when transmitting Gossip and Trust payloads. Apps MUST use HPKE _Base Mode_ so recipients can always decrypt messages and senders don't leak information about themselves in transport headers. It ensures an ephemeral key gets generated for each message. Senders will get authenticated via their signature (see Gossip, Trust, and Envelopes). The HPKE `info` parameter MUST contain raw bytes of the recipient's ledger key so the payload is contextually bound to it.


### Payload Format

The Gossip and Trust protocols (see Gossip and Trust) typically send payloads with more than one (text or binary) file. Both treat payloads as atomic units of transmission, and assume the transport will just work. And almost always, stream-based APIs ensure it will.

Apps MUST exchange Gossip and Trust payloads enveloped in flat CBOR maps (RFC 8949), without its optional self-describing tag, where values are the raw bytes of the files being sent, and keys are their string-encoded Content Identifier (see Identifiers):

    {<cid>: <bytes>, ...}

This envelope format packs the information needed to check the integrity of the payloads before processing, without embedding predictable meta-information like MIME file headers or zip magic numbers or CBOR self-describing tags that could be used as a plaintext oracle or crib during cryptanalysis of the payload.

Apps MUST compress this CBOR map using raw DEFLATE (RFC 1951, without the ZLIB header or GZIP wrapper). Compression is valid here because the Gossip and Trust APIs only respond to requests authenticated using ledger keys, so there are no high traffic strings being exchanged (like browser cookies) that could be used as compression oracles for CRIME- or BREACH-like attacks.

Apps MUST encrypt this compressed payload using HPKE (see Secure Channels).

Apps MUST wireframe this encrypted payload by adding the first 4 bytes of the sender's fingerprint for that transmission channel (see Fingerprints), so the payload's recipient can zero in on how to decrypt the payload without trying every key:

    [ 4-Byte Fingerprint ] [ HPKE Ciphertext ]

The fingerprint's high entropy and position make it look like encrypted data to a first time observer. In principle, it could be used as an oracle by analyzing traffic over time. In practice, the fingerprint is unique per counterparty pair and per transmission channel, and ledgers will have revealed their relationship to a traffic analyzer anyway. Plus, either counterparty can rotate their ledger key to change the fingerprint (see Key Rotations).

Most communication transports with be happy with this fingerprinted payload as is. Lower level ones, like Bluetooth L2CAP byte streams, need apps to manually communicate payload boundaries. In such cases, apps MUST add an extra 4-byte, big-endian unsigned integer header with the fingerprinted payload's byte size:

    [ 4-Byte Size ] [ 4-Byte Fingerprint ] [ HPKE Ciphertext ]

Apps that want to support exotic transports like radio-frequency-based ones may need to chunk payloads and handle the stream fragmentation and reassembly.


### Steganography

Apps MAY encode wireframed payloads (see Payload Format) inside media files to overcome hostile transmission contexts.

Steganography is vendor-driven, but needs a mention because transport channels can face delivery problems. Corporate email gateways routinely block encrypted payloads they can't open and inspect, for instance. The workaround is to give corporate security your private key, but that is not always sane or practical.

On the flip side, steganography algorithms are many, not always maintained, and not always compatible for the same name (see `f5stegojs` and `F5Py`). So there is very little to latch onto except conventions on the address proof arguments to use (see Address Proofs).

Apps MUST reserve and recognize the `stego` address proof argument to signal a steganography requirement, and MUST NOT send payloads to that address if they cannot honor that steganography requirement. The `stego` argument MUST contain a case-insensitive steganography algorithm identifier. Any other argument used alongside it is vendor or algorithm specific.

Vendors SHOULD namespace steganography identifiers behind a `vendor:<name>:` prefix to avoid collisions until enough vendors agree on the semantics. Heeding this suggestion will help avert the interoperability problems that plagued early internet browsers.

The goal here is getting past the email filter, not cryptographic obfuscation. If you're concerned about the latter, you shouldn't be using a fingerprint to know which ledger sent you a transaction. Also, local transports like WiFi or Bluetooth don't need steganography, since apps are communicating directly.


### Bootstrap Handles

Apps MUST support emitting, recognizing, and processing plaintext bootstrap handles so ledgers can discover each other's public keys and API endpoints.

A bootstrap handle's data MUST be a flat, integer-indexed CBOR map (RFC 8949). The first index (`0`) MUST be the multiformat-prefixed raw bytes of the ledger key used in its `did:key` formatted identifier (see Identifiers). Subsequent indexes, if any, MUST be scheme-prefixed API endpoints (see Address Proofs). Bootstrap handles MUST be base64url encoded without padding (RFC 4648) when shared.

    {
      0: <multiformat_prefixed_key_bytes>,
      1: "ble:<broadcasted_uuid>:<psm>",
      2: "http://<local_ipaddr>:<port>"
    }

Using `http` for endpoints is adequate since payloads are encrypted using HPKE, and spares end-users those pointless certificate-related warnings that browsers have long conditioned everyone to ignore.

Apps MAY omit any or all of the API endpoints they expose in bootstrap handles, and SHOULD omit the addresses of non-interactive transports by default. A local endpoint makes sense in proximity-based contexts only, and sharing your email or phone number with random strangers is seldom desirable.

Apps MUST support sharing and manually consuming bootstrap handles prefixed with the custom `p2pledger:` URI scheme. This format allows inserting bootstrap handles as URIs in emails, web pages, transaction envelopes (see Envelopes), NDEF (NFC Data Exchange Format), or QR codes:

    p2pledger:<base64url_encoded_cbor_data>

Apps MUST support sharing and manually consuming bootstrap handles as `p2pledger=` entries in mDNS/DNS-SD (RFC 6762/6763) TXT records:

    p2pledger=<base64url_encoded_cbor_data>

Email- and browser-based apps MAY support sharing and automatically consuming bootstrap handles as email and HTTP headers using the `P2PLedger` key:

    P2PLedger: <base64url_encoded_cbor_data>

(Note that corporate email gateways routinely strip headers, so apps SHOULD NOT depend on `P2PLedger` headers. They're intended as helpful workflow automations when they work, nothing more.)

Email- and browser-based apps MAY support sharing and automatically consuming bootstrap handles in HTML emails and web pages as `<meta name="p2pledger">` tags:

    <meta name="p2pledger" content="<base64url_encoded_cbor_data>">


## Privacy

Apps MUST encrypt any data they hold in storage and in transit. Vendors SHOULD use their best judgement on where to draw the line: unencrypted data in RAM is impractical to avoid, but that doesn't make unencrypted data in Memcached okay.

Apps MUST encrypt and sign communications with other apps except as needed to first establish a secure and authenticated communication channel, and MUST flatly deny all other interactions to not leak meta-information.

Apps MUST authenticate ledger controllers (see Authentication) before granting them access to the data the app holds, whether for use inside it, or outside it using transaction protocols (see Gossip and Trust) or other APIs that grant access to that data, nominal or anonymized, as records or aggregates, for any purpose---analysis, audits, reporting, load balancing, anything.

Uncompromising transaction privacy is a simple matter of creating new ledgers. Fill them directly or through intermediaries so they look creditworthy (see Intermediaries), exactly like you'd fill or pay someone to fill a prepaid card. With this said, transactions usually need to be kept confidential rather than made anonymous, and creating a new ledger is overkill in that case.

Transaction confidentiality is a simple matter of having a payment intermediary pay the bill. This guarantees that the Trust protocol, which normally reveals a non-zero balance along with direction and magnitude hints to help consolidate debt loops, leaks nothing---since the intermediary consolidated the transaction at payment time. Apps SHOULD offer UI (a checkbox) to enable ledger controllers to mark some or all transactions as confidential and automate enforcing that an intermediary pay the transaction in full.

Vendors SHOULD adopt the mindset that the best way to not leak information---or worse, find it dumped in a data breach---is to not ask for it to begin with. As such, Apps SHOULD NOT require personally identifiable information beyond what's needed for permission control (see Authorizations) and what end-users volunteer inside the transactions themselves.


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


### Ledger Recovery

Apps MUST implement a 7-day grace period whereby any proof that has been active for 7 days or more **remains valid** for the duration of the grace period after being invalidated. This enables recovering from scorched-earth scenarios where an attacker who acquires the key rotates it and burns the bridges to lock out the ledger's owner.

Apps MUST broadcast all proof changes to applicable address proofs (typically email or phone notifications) that are active (including those that just got cancelled and remain valid for a grace period) so proof changes don't escape the attention of ledger controllers. Apps MUST include a rescue link in these notifications.

Invoking an invalidated proof using such a rescue link during this grace period MUST transition the ledger into a Disputed state. When in a Disputed state, the app MUST temporarily suspend all proofs added in the past 7 days except the one used with the rescue link, and disallow signing any transaction except the one needed to re-approve or repudiate these proofs.

If all else fails, the Dead Ledger process enables liquidating a locked ledger provided it was part of a community (see Communities). The process mirrors an off-graph inheritance under the supervision of an authority, with the latter holding the authorization needed to transfer the balance.


### Authorizations

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


## Forensics

Apps MUST maintain an append-only log for their transaction history. This log MUST compute its next hash based on the data being logged, its previous state, and the local timestamp. Apps MUST document their hashing algorithm in the log as meta (like Git) or directly in the data to ensure the log stays auditable when the algorithm changes.

This transaction history is not intended to synchronize hashes much less full logs between ledgers, nor is it intended for any type of consensus automation. It does not even try to be those things.

Rather, it is an append-only record of locally timestamped events that arrive asynchronously on disparate devices whose clocks are likely out of sync and possibly tampered with. Anyone using this as forensic evidence SHOULD assume timestamps in this log are dubious. Events could get logged long after they've been sent, so not even local timestamps can be trusted, and no assumption can be made about the event order and hashes across replicas of the same ledger.

What the log is intended to provide is a tamper-resistant record of the order in which _local_ events containing _non-local_ references get committed to the log. Put another way, ledgers exchange encrypted information about their state as they interact, and embed that information into their own future state. These entangled histories make rewriting a ledger's transaction history impossible without also rewriting that of nearby ledgers on the graph to cover it up.

This tamper-resistant evidence of consideration and intent makes transactions on this graph _far more_ enforceable than they'd be with a mere cryptographic signature, and the dispute resolution process (see Disputes) offers repudiation guarantees in case of private key misuse that a blockchain cannot match without Orwellian levels of control.

Fittingly, this tamper-resistance is socio-cryptographic rather than absolute. Consider a gaslighting attack, where an adversary coordinates rewrites around a node until it abdicates its own judgement to its context. The parallels with conformity and deference to authority are striking [@Asch1956; @Milgram1963]. We'll flesh out the link with cognition later.

These logs' most interesting property is the way they enable sequencing events without synchronized wall clocks, and defining topologies on the graph. This ties into spacetime and causal set theory, but that discussion will wait too. What matters for our sake is that this gives these logs strong forensic value. With this in mind:

Apps MUST log every decision (manual or automated) related to transmissions in each affected ledger's transaction history (see Gossip, Trust, and Logging). The log entries MUST include every relevant ledger key and signature, the proof or repudiation or transaction contract and attachment CIDs, docket IDs (see Docket IDs), and other receipts that could be needed in a dispute. The Logging section has the format details.

Apps MUST log CIDs instead of contracts and attachment files to limit clutter, since a CID is enough to characterize these. Apps MUST store the relevant files and make them available for retrieval for a reasonable duration (see Gossip). A mobile app MAY defer to a main device it is kept in sync with for the parts.


### Integrity

Apps MAY store any information they need to audit past transactions (such as IDs, public keys, signatures, etc.), and MUST gracefully handle losing access to that information. This ensures apps can safely purge old data, or change their hashing algorithm or public key or other state without disrupting the transaction graph or their ability to audit their own data.

As noted earlier, Apps MUST store files and blobs outside of their transaction history, and instead refer to them by their CID in its logs (see Identifiers). In practical terms, this enables maintaining an index of where files are and using their CID in separate log entries to avoid clutter and save space.

Apps MAY purge the files related to stale (unfinalized) or archived (finalized) transactions, but MUST retain the logs, since those are required to check the log's integrity. Apps MAY pack and otherwise compress old log entries to save space.

Apps SHOULD warn end-users that purged data cannot be used in disputes when they first purge data or turn on automations to that effect.


### Docket IDs

Conceptually, transaction docket IDs are exactly like the references used in bureaucratic communications---with the twist that the reference changes due to new docket IDs being generated as ledgers interact. Docket IDs are named after legal dockets, which are the courthouse equivalents of append-only logs.

Apps MUST log a transaction's contract CID (see Contracts) before sharing any transaction, MUST use the commit hash of that log entry as that transaction's reference ID, and MUST add or update that ID in the transaction's envelope when gossiping it (see Envelopes and Gossip). This ensures a transaction's reference ID cannot be tampered with---a different transaction or the same one committed later would yield a different reference ID.

Apps MUST include the reference IDs of other participants and the reference ID it sets when sending transactions (see Gossip).

Apps MAY include more than one reference ID. This matters for end-users with more than one device. Apps that cannot locate a reference ID in their ledger's transaction history SHOULD assume another device set the ID, let it be, and generate or update their own reference ID only.

Apps MUST NOT confuse reference IDs and transaction IDs. A transaction's ID is the contract's CID (see Identifiers). In distributed systems, the Reference ID is sometimes known as the tracking or intent ID, and the Transaction ID as the resultant ID. The first is intended as a database key during negotiations, and as proof of consideration and intent. The other, as the legal seal of what the transaction's participants agreed on and _signed_.


### Wall Clocks

The unreliability of wall clocks may need stressing for non-technical readers. Computers use internal oscillators to track time and NTP servers (Network Time Protocol) as their external source of truth. A computer's wall clock could be tampered with, the reference server it's deferring to could be lying, and the routers in between them could be lying too. Adding insult to injury, NTP pools aren't secure, so your choices are trusting a secure but specific NTP provider (plague) or trusting that no one is inside your router (cholera).

Transaction participants set signature deadlines and authorization expirations all the same, so we need to mind wall clocks usage in deadlines and delegated signatures (see Promises and `/sign` Authorizations). Not all wall clock checks are made equal, however, because some transactions are harder to reverse from the perspective of of the graph.

Critical transactions add or revoke proofs, or assign an executable action to _any_ of its signers (see Instructions). The first allows adding or removing a ledger controller. The other, anything a script can do, so could trigger a wire transfer or a cryptocurrency transaction. Given the stakes, a fresh wall clock check when signing or verifying the signature of such transactions makes sense.

Non-critical transactions can be more lenient. Off-graph due diligence is still be warranted before releasing, shipping, or clearing what needs to be, but the tradeoff tilts toward making ledgers work offline since the transaction itself can be disputed as fraudulent and reversed. With this context in mind:


### `clock-sync` Entries

A `clock-sync` entry is a log entry with a `clock-sync` line:

    parent f12205f795...
    ledger z4MgZB... 2026-04-10T14:30:00Z
    
    clock-sync: 71647/2026-04-10T10:30:00Z

The `clock-sync` line has two times: the monotonic clock time, and a reference UTC wall clock time in ISO 8601 Extended format, both with whole seconds. The log entry's metadata also holds the system UTC wall clock time (see Logging).

Disparities in such log entries merely show that the clocks disagreed. Perhaps the reference is off, or a device had a flat battery, or the network was down, or something else. The crumbs don't matter---it's the trail that does.


### Gossip-Based `clock-sync` Checks

A routine `clock-sync` entry is needed when the last `clock-sync` entry logged:

- Had no monotonic clock or reference wall clock entry (`-`, see below); or

- Was logged in the future according to the monotonic clock; or

- Was logged 60 seconds or more in the future according to the system wall clock; or

- Was logged 900 seconds or more in the past according to the system wall clock or the monotonic clock (check both).

In other words, a routine clock sync is needed every 15 minutes unless the last entry suggests it occurred in the future (due to a bad wall clock or a reboot), with a generous margin of a minute in case NTP is doing its thing (the protocol invites speeding up or slowing down the wall clock when it's not too off).

Apps MUST track the timestamps of incoming gossip transmissions sent by trusted participants over interactive channels (see Gossip, Trust, and Logging). These normally happen and time out quickly. Not always, to be clear, but often enough that they can help reveal a system wall clock that's off. Apps MUST add a `clock-sync` line with the timestamp of such transmissions in the gossip log entry when:

- That timestamp and the system wall clock are off by 300 seconds or more, to flag the discrepancy; or

- The last `clock-sync` entry has a wall clock time that showed they were off by a 300 seconds or more, to signal when the discrepancy stopped; or

- A routine `clock-sync` entry is needed, as a heartbeat.

In other words, log every 15 minutes as gossip arrives in the normal case, and keep logging discrepancies of 5 minutes or more until they stop otherwise. That gives us a stream of pushed signals. Let's now pair those with pulled signals.


### NTS-Based `clock-sync` Checks

Apps MUST support logging a `clock-sync` line using NTS (NTP over TLS, RFC 8915), as follows:

1. Note the current monotonic clock time.

2. Query four NTS servers in parallel, picked at random from a preconfigured pool. Ideally use a user-configurable pool, since firewalls might block NTS and the servers to pick from can be scarce in some geographies.

3. If the device was offline or the NTS servers all timed out, use `-` as the reference wall clock value. Else strip out the responses that timed out and use their median value, rounded to the nearest second.

4. If the monotonic clock time did not move forward, use `-` as the monotonic clock time, else use the current value, rounded to the nearest second.

5. Log the `clock-sync` line with the monotonic and reference wall clock values.

Apps SHOULD do NTS-based `clock-sync` checks inside a Mutex-protected process to avoid redundant checks when more than one concurrent transaction triggers them.


### Critical Transactions

_Before_ using the wall clock while signing or verifying the signature of a transaction that adds or revokes proofs or assigns executable actions to _any_ of the signers, apps MUST log a `clock-sync` line using NTS if the last `clock-sync` entry logged:

- Has no `signed`, `accepted`, or `rejected` line (see Signature Logging); or

- Has no monotonic clock or reference wall clock entry (`-`); or

- Was logged in the future according to the monotonic clock; or

- Was logged 60 seconds or more in the future according to the system wall clock; or

- Was logged 60 seconds or more in the past according to the system wall clock or the monotonic clock (check both).

In other words, require a deliberate and very fresh (1 minute) _successful_ wall clock check before using it for critical transactions.

Apps MAY be even stricter by systematically requiring these NTS-based checks. They're periodic by default because edge devices will typically do them anyway due to infrequent transactions, and busy servers will typically value the lower overhead of doing them periodically (with a cron triggering those, at that, to avoid blocking).

When _using_ the wall clock while signing or verifying the signature of a transaction that adds or revokes proofs or assigns executable actions to _any_ of the signers, apps MUST analyze the `clock-sync` line that was logged or found to be fit for purpose per above, and reject the signing or verification process with a `rejected` log line and an invalid wall clock error, if that log line:

- Has no monotonic clock entry (`-`) or reference wall clock entry (`-`); or

- Revealed that the reference wall clock and the system wall clock are off by 60 seconds or more in either direction.

It's worth stressing that the real hurdle here is not spoofing the clock while signing. Rather, it is that the verifier's clock is the only one that matters.

A malicious actor _could_, in principle, freeze the clocks of ledgers they have physical access to after the NTS checks---but they might as well beat you with a wrench if they're that dedicated (XKCD 538).


### Non-Critical Transactions

_Before_ using the wall clock while signing or verifying the signature of any other transaction, apps MUST log a `clock-sync` line using NTS if the last `clock-sync` entry logged:

- Has no `signed`, `accepted`, or `rejected` line; or

- Has no monotonic clock or reference wall clock entry (`-`); or

- Was logged in the future according to the monotonic clock; or

- Was logged 60 seconds or more in the future according to the system wall clock; or

- Was logged 900 seconds or more in the past according to the system wall clock or the monotonic clock (check both); or

- Revealed that the reference wall clock and the system wall clock are off by 60 seconds or more in either direction.

Apps MAY be stricter by requiring more frequent NTS-based checks.

When _using_ the wall clock while signing or verifying the signature of any other transaction, apps MUST analyze the `clock-sync` line that was logged or found to be fit for purpose per above, and reject the signing or verification process with `rejected` log line and an invalid wall clock error, if that log line:

- Has no monotonic clock entry (`-`); or

- Has a reference wall clock entry that revealed the reference wall clock and the system wall clock are off by 60 seconds or more in either direction.

Apps MAY use the wall clock as is if the log line has no reference wall clock entry (`-`). The point is gathering evidence of potential wall clock tampering, while letting devices work offline. Plus, offline devices will typically trust one another enough to produce gossip-based `clock-sync` entries as a background signal anyway.


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

Vendors SHOULD get into 30-minute calls with a half-dozen end-users every now and then instead. Ask what they use your app for, how they use it, and where it gets in their way. A half dozen is a sweet spot that will surface most issues. You'll get far more actionable information about your app and market than from tracking data. Then follow up. A delighted end-user sends referrals like their life depends on it.
