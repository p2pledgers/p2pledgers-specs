# Security

\epigraph{Privacy is necessary for an open society in the electronic age.
}{Eric Hughes, Cypherpunk's Manifesto (1993)}

An important goal that permeates this document is ensuring no single party can become an all-powerful middleman that controls part or all of the transaction graph.

The threat model assumes adversarial or careless vendors, end-users, apps, and infrastructure, and that transactions around end-users you trust are the only source of trust.

Apps SHOULD use adequate security protocols, and MAY refuse to interact with apps for any reason, including but not limited to inadequate security.


## Secure Channels

Transmissions in this protocol are asynchronous and transport-agnostic, so as to not depend on any infrastructure, with built-in handling of failures like lost devices, dead endpoints, handshakes that cross payloads, and other race conditions (see Gossip and Transmissions).

As a result of this design choice, transmissions are stateless. Messages arrive out of order on different devices tied to the same ledger with no coordination beyond a periodic log exchange (see Synchronization). This precludes managing a ratcheting state, since four devices holding two ledgers might be communicating with one another in any order and be woefully out of sync.

Asynchronous transport-agnosticism also rules out using TLS (RFC 8446) or EDHOC (RFC 9528), since those can't be used to transmit payloads using email or file drops. Hybrid public key encryption (HPKE; RFC 9180) is thus our only sensible encryption option. Its updated and post-quantum versions are active drafts at the time of writing [@IETF-HPKE; @IETF-HPKE-PQ]. Because ledgers can be hosted on more than one device, payloads get encrypted using the hybrid cryptographic envelope pattern (CEK; see Encryption).

Transmission endpoints can serve multiple ledgers at the same time, and those endpoints can serve other purposes (like email). Apps therefore need a way to identify transmissions tied to this protocol, their sender, and their intended recipient. This protocol assigns fingerprints to specific senders or purposes to that end (see Fingerprints and Endpoint Discovery). These fingerprints could be used for tracking in theory, so this protocol takes several steps to shield them from view.

The first of these is hash-based challenges that protect endpoints from abuses (see Challenges). Challenges are derived from fingerprint-specific tokens (see Transmission Tokens) and the payload being sent. The full fingerprint, which is not sent on the wire, is needed to configure and solve these challenges.

The challenge's result and the full fingerprint get used to derive a symmetric key. The latter gets used to wrap the actual payload in an outer envelope (see Wire Format). This provides a second encryption layer that can only be pierced by knowing the full fingerprint.

The point of this outer envelope is obfuscation, but it offers confidentiality as a convenient side-effect. To wit, the outer envelope's symmetric key depends on 32 secret bytes. It is thus quantum-resistant to an observer that does not known the full fingerprint. The fingerprint used to establish secure channels in handshakes typically get shared by HTTPS, Bluetooth, or NFC. The first two are encrypted; the last is impractical to monitor. The fingerprints used after establishing secure channels are derived from their pre-shared keys. It follows that outer envelopes usually offer confidentiality for the public keys and the HPKE encrypted payloads inside them.

The last of these steps is a one-time transmission tag that allows obfuscating and deriving the full fingerprint and token data from what gets transmitted on the wire (see Transmission Tags). Tags enable recipients to read the only four bytes of the fingerprint that get XOR-obfuscated on the wire. The hash derived from the tag and the full fingerprint allows reading the XOR-obfuscated token. An integrity check allows confirming that the token is tied to the fingerprint, thus validating both. The tag doubles as an integrity check for the wire as a whole, for further protection against abuses and replay attacks.

In principle, an observer could use the XOR-obfuscated bytes of fingerprints as a beacon. This risk is only theoretical, because an observer would need to know what traffic is related to this protocol to tell apart fingerprinted payloads from false positives in the larger pool of encrypted traffic. Plus, monitoring fingerprints transmitted via HTTPS, Bluetooth, or NFC is just impractical. That limits monitoring to unencrypted channels like emails and HTTP traffic on local area networks. An observer doesn't need an extra fingerprint to tell them that John and Jane are exchanging in such cases---transport metadata will have told them that already.

Challenges are checked in constant time to avoid leaking information that might get used in side-channel attacks. Recipients then close the connections tied to failed challenges and duplicate requests to save bandwidth. Automations adjust the threat level during and after attacks (see Threat Management). Legitimate senders caught in the cross-fire get fresh tokens through throttled responses. Illegitimate requests can slip through as a result of accommodating the latter. Those would depend on an attacker completing challenges without triggering the duplicate request filter while the threat level is rising automatically---and they'd get no response.

In sum, the transmission format is high entropy from head to tail to observers, protects endpoints from abuses like distributed denial of service attacks, and enables recipients to identify the decryption key they'll need to use with HPKE before even opening the payload's envelope---for the cost of an `O(1)` look-up and a few hashes.


## Primitive Support

Cryptography evolves constantly, so recommending any specific primitive would guarantee eventual obsolescence. Plus, there is more to primitive selection than security:

* Good primitives are ubiquitous enough to work out-of-the-box without draining phone batteries flat, and good cipher suites balance security with the needs of low-end, storage-constrained devices.

* What other apps want to use necessarily dictates what apps ought to support, and what other apps support dictates what an app can use.

* This protocol uses CBOR (Concise Binary Object Representation, RFC 8949) Object Signing and Encryption (COSE; RFC 9052; RFC 9053) and User Controlled Authorization Networks (UCAN; @UCAN), which overlap with JSON Object Signing and Encryption (JOSE; RFC 7515; RFC 7516; RFC 7517; RFC 7518; RFC 7519).

* The use of COSE with post-quantum primitives and hybrid public key encryption (HPKE; RFC 9180) is being normalized at the time of writing [@IETF-COSE-HPKE; @IETF-COSE-HPKE-PQ; @IETF-COSE-SIGS-PQ].

In that light, apps SHOULD limit the primitives and cipher suites they offer to, and MUST support, those with:

1. A well-defined IETF-recommended identifier for use in COSE as part of a cipher suite or as a signature algorithm; and

2. A well-defined, inherent hash function natively used by the primitive or its cryptographic family (for pre-hashing payloads before signing them, or internal transformations like the Fujisaki-Okamoto transform), with hybrid keys using the hash function of their primary (post-quantum) component.

Usage is the critical "well-defined" factor in the above: what matters for an IETF-recommended identifier is that libraries support those identifiers, not that they've a finalized number. The IETF-recommended lists effectively serve as peer-maintained lists of widely supported, well-defined primitives.


## Primitive Shortlist

At the time of writing, this narrows down the primitives that apps MUST support to a handful of modern ones:

* P-256, P-384, P-521, X25519, X448, ML-KEM-512, ML-KEM-768, ML-KEM-1024, ML-KEM-768 + P-256, ML-KEM-768 + X25519, and ML-KEM-1024 + P-384 as key exchange mechanisms (KEM). The ML-KEM ones offer quantum-resistant key exchanges.

* SHA-256, SHA-384, SHA-512, and SHAKE-256 key derivation functions (KDF).

* AES-128-GCM, AES-256-GCM, and ChaCha20-Poly1305 for authenticated encryption with associated data (AEAD).

* P-256, P-384, P-521, Ed25519, Ed448, ML-DSA-44, ML-DSA-65, ML-DSA-87, ML-DSA-44 + P-256, ML-DSA-65 + P-256, ML-DSA-87 + P-384, ML-DSA-44 + Ed25519, ML-DSA-65 + Ed25519, and ML-DSA-87 + Ed448 for signatures. The ML-DSA ones offer quantum-resistant authentication.


## Primitive Selection

The need to support these primitives and cipher suites for interoperability does not mean apps need to expose them to users by default.

Apps SHOULD NOT offer to use P-256, P-384, or P-521, or their associated cipher suites, without a hardware enclave. These both depend on a high-quality random number generator with each use. A lack thereof led to the Sony PS3 hack in 2010 and Bitcoin Wallet hacks in 2013 and 2014. Hardware enclaves offer the entropy guarantees needed to avoid this issue. Apps on devices that lack one MUST NOT even offer cipher suites that use them as options (see Handshakes).

Apps SHOULD skip offering P-256, P-384, or P-521 altogether, in fact, except as needed for government compliance. These primitives are seldom useful outside of legacy-NIST compliant circles, and even there, CNSA 2.0 is phasing them out in favor of hybrid ML-KEM-1024 + P-384 and ML-DSA-87 + P-384 primitives.

Apps SHOULD prefer Ed25519/X25519 over P-256, except perhaps under the hood as the master key (see Public Keys) used to encrypt the app's data. Ed25519/X25519 alleviates the need for a high-quality random number generator with each use, and optimized Ed25519/X25519 software often matches or beats the performance of P-256 with hardware-acceleration. Apps SHOULD prefer Ed448/X448 over P-384 and P-521, for the same reasons.

Apps SHOULD default to using AES-128-GCM or AES-256-GCM. ChaCha20-Poly1305 gets used in IoT settings to avoid the performance cost associated with preventing cache-timing attacks when AES hardware acceleration (AES-NI) is not available. AES-NI is so ubiquitous on modern devices that the only scenario where it won't be is a misconfigured virtualized environment with plenty of CPU to spare.

Post-quantum primitives offer quantum-resistance but demand a brief discussion to clear out potential misconceptions and set expectations.

First and foremost, paranoid-level security is overkill. The only exception is if an intelligence agency is targeting you---and if they are, they hacked into your phone long ago, so ML-KEM-1024 and ML-DSA-87 are not going to help much.

Secondly, quantum-resistant cryptography addresses a hypothetical threat. The issue is not that Ed25519/X25519 is insecure. Rather, it is that experts are warning Shor's algorithm could break it in a decade or so. They've been doing so for the past two decades. National security outfits are leading this charge, so this reeks of the usual military-industrial complex bogeyman to plunder the public's purse for the benefit of private pockets.

Next, there is no cryptocurrency-like finality in this protocol (see Disputes), so post-quantum security and authenticity guarantees, while great on paper, are simply not worth the key and signature size bloat they impose. ML-DSA keys are overkill until the quantum threat materializes, since the utility of a signing key is ephemeral when authenticating a payload, and no one is going to forge a signature for a backdated transaction that would simply get disputed in the off chance the signing key had not been long revoked.

Lastly, you can use a large enough symmetric key to address the "harvest now, decrypt later" threat, since Grover's algorithm only halves their strength. In a traditional curve-based HPKE context, that means a large enough pre-shared key. The question then becomes how to exchange PSKs securely. This protocol's answer is to use a quantum-resistant cipher suite when exchanging PSKs (see Public Keys and Handshakes). That allows using traditional curve-based keys until the quantum threat materializes.

That approach addresses the major issue with post-quantum keys, which is their size. A 1,184-byte ML-KEM-768 key doesn't seem like much until users shop with anonymized keys (see Privacy). Multiply that by counterparties, and it quickly balloons to gigabytes worth of public keys for a connected enough ledger---or terabytes for a large enough corporation. The storage requirements are asinine for a threat that might not materialize for decades longer.

ML-DSA-44, ML-DSA-65, and ML-DSA-87 keys fare no better for signatures.

ML-DSA-44, ML-DSA-65, and ML-DSA-87 can also be slow depending on the hardware. This protocol depends on signing a batch of payloads in near-real time in some situations (see Trust), so apps SHOULD make sure a device is capable of signing a few dozen payloads in acceptably low time before offering ML-DSA keys. That low time is in fact very low, because trust-related payloads make round-trips on the web after getting signed, and users notice they're waiting after around 150 ms. On the flip side, the yardsticks to compare them with are credit card terminals, and it's not like those are blazing fast either.


## Cipher Suite Selection

Apps MUST support cipher suites HPKE-3-KE, HPKE-4-KE, HPKE-5-KE, HPKE-6-KE, HPKE-9-KE, HPKE-11-KE, HPKE-12-KE, and HPKE-13-KE, and SHOULD support the others suites based on what hardware enclaves allow.

+============+=====================+===========+===================+
| COSE-HPKE  | KEM                 | KDF       | AEAD              |
+============+=====================+===========+===================+
| HPKE-0-KE  | P-256               | SHA-256   | AES-128-GCM       |
| (46)       | (0x0010)            | (0x0001)  | (0x0001)          |
+------------+---------------------+-----------+-------------------+
| HPKE-1-KE  | P-384               | SHA-384   | AES-256-GCM       |
| (47)       | (0x0011)            | (0x0002)  | (0x0002)          |
+------------+---------------------+-----------+-------------------+
| HPKE-2-KE  | P-521               | SHA-512   | AES-256-GCM       |
| (48)       | (0x0012)            | (0x0003)  | (0x0002)          |
+------------+---------------------+-----------+-------------------+
| HPKE-3-KE  | X25519              | SHA-256   | AES-128-GCM       |
| (49)       | (0x0020)            | (0x0001)  | (0x0001)          |
+------------+---------------------+-----------+-------------------+
| HPKE-4-KE  | X25519              | SHA-256   | ChaCha20-Poly1305 |
| (50)       | (0x0020)            | (0x0001)  | (0x0003)          |
+------------+---------------------+-----------+-------------------+
| HPKE-5-KE  | X448                | SHA-512   | AES-256-GCM       |
| (51)       | (0x0021)            | (0x0003)  | (0x0002)          |
+------------+---------------------+-----------+-------------------+
| HPKE-6-KE  | X448                | SHA-512   | ChaCha20-Poly1305 |
| (52)       | (0x0021)            | (0x0003)  | (0x0003)          |
+------------+---------------------+-----------+-------------------+
| HPKE-7-KE  | P-256               | SHA-256   | AES-256-GCM       |
| (53)       | (0x0010)            | (0x0001)  | (0x0002)          |
+------------+---------------------+-----------+-------------------+
| HPKE-8-KE  | ML-KEM-768 + P-256  | SHAKE-256 | AES-256-GCM       |
| (55)       | (0x0050)            | (0x0011)  | (0x0002)          |
+------------+---------------------+-----------+-------------------+
| HPKE-9-KE  | ML-KEM-768 + X25519 | SHAKE-256 | AES-256-GCM       |
| (57)       | (0x647a)            | (0x0011)  | (0x0002)          |
+------------+---------------------+-----------+-------------------+
| HPKE-10-KE | ML-KEM-1024 + P-384 | SHAKE-256 | AES-256-GCM       |
| (59)       | (0x0051)            | (0x0011)  | (0x0002)          |
+------------+---------------------+-----------+-------------------+
| HPKE-11-KE | ML-KEM-512          | SHAKE-256 | AES-128-GCM       |
| (61)       | (0x0040)            | (0x0011)  | (0x0001)          |
+------------+---------------------+-----------+-------------------+
| HPKE-12-KE | ML-KEM-768          | SHAKE-256 | AES-256-GCM       |
| (63)       | (0x0041)            | (0x0011)  | (0x0002)          |
+------------+---------------------+-----------+-------------------+
| HPKE-13-KE | ML-KEM-1024         | SHAKE-256 | AES-256-GCM       |
| (65)       | (0x0042)            | (0x0011)  | (0x0002)          |
+------------+---------------------+-----------+-------------------+

The `uint16` codes are the IANA-registered hybrid public key encryption (HPKE; RFC 9180) algorithm identifiers at the time of writing [@IANA-HPKE-Codes]. The HPKE cipher suite values are from the active COSE-HPKE drafts [@IETF-COSE-HPKE; @IETF-COSE-HPKE-PQ].


## Recommended Primitives

On the basis of the above, apps SHOULD expose and default to a 128-bit "High Security" cipher suite (HPKE-3-KE) with regularly rotated X25519 transport keys (KEM), SHA-256 (KDF), AES-128-GCM (AEAD), and a longer-lived Ed25519 identity key for signing (see Public Keys). The 32-byte PSKs shared in quantum-resistant handshakes ensure this cipher suite will be secure when (if) the quantum threat materializes---and the quantum-resistant outer envelopes keep the HPKE payloads themselves secure (see Secure Channels).

Apps MUST use a quantum-resistant cipher suite during handshakes. Either of the 128-bit post-quantum cipher suites are RECOMMENDED for that purpose---the pure post-quantum ML-KEM-512 one (HPKE-11-KE), or the hybrid ML-KEM-768 + X25519 one (HPKE-9-KE) for defense-in-depth.

Handshakes enable ledgers to force another to use a cipher suite to some degree (see Handshakes), so a peer-to-peer-led post-quantum transition that works even if vendors fail to update app defaults and end-users fail to update their apps is baked into this protocol if the quantum threat ever materializes.


## Public Keys

Apps MUST expose one public key per ledger as its identity key, or (ledger) key for short, and MUST use this key to sign its transactions and authenticate its transmissions (see Signatures and Transmissions).

Apps MUST expose at least one public key per ledger as its transport key, and MUST share such transport keys with other ledgers so the latter can encrypt payloads for that ledger.

Apps MUST assign exactly one transport key to the identity key of each ledger it interacts with, and MUST maintain at least one short-lived, post-quantum transport key assigned to no specific ledger for use inside handshakes (see Handshakes).

Apps MUST pair each public key they create with a fresh 32-byte secret, except as needed when devices are paired (see below), and MUST generate these secrets using an adequate entropy source. These secrets enable computing the tokens and fingerprints needed to route transmissions (see Fingerprints).

These specifications use a ledger's pre-shared key (PSK) with another ledger to mean the secret that ledger paired with the transport key it assigned to that other ledger.

Apps MUST use handshakes to initially share and subsequently rotate identity keys, transport keys, and PSKs with other ledgers. Apps MUST refresh transport keys and PSKs with each handshake unless the last one occurred less than a day ago. This ensures users can impose their security schedule on one another to a large degree without inviting spam. Apps MUST honor transport keys and secrets for a reasonable duration after rotating them to ensure payloads that cross handshakes on the wire or wait for days on end as file-drops in a web folder can still be decrypted.

Transport keys are often called (recipient) ephemeral keys, and security best practices are to make them short-lived. They typically get rotated after a few uses (or even one) or some period of time, to limit what a compromised private key can decrypt and guarantee forward secrecy. Practicalities make it routine to keep transport keys semi-static outside of web server contexts. Apps MUST NOT make storage assumptions about other apps beyond the requisite transport keys assigned to their ledgers' identity keys. In particular, apps SHOULD NOT spam single-use transport keys, because apps MAY legitimately ignore them all except one.

Apps SHOULD periodically rotate transport keys. There is no correct rotation policy, so the specifics are at vendors' and users' discretion. But note that, in the asynchronous spirit of this protocol, not scheduling rotations at all works fine: check the time since the last rotation upon receiving a payload, and initialize a handshake after the ongoing interaction if the last rotation occurred too long ago. That keeps rotations regular without any scheduling or device synchronization hassles.

Apps MUST NOT share the private keys associated with any of their public keys with apps on any other device---not even other apps that hold the same ledger.
In the interest of clearing any doubts about what this entails:

* One app can hold several ledgers. Each ledger has exactly one active identity key, at least one active post-quantum transport key for use in handshakes, and exactly one active transport key per ledger it interacts with. Ledgers can also hold any number of inactive keys.

* Conversely ledgers hold the active identity key and the active transport key of every other ledgers it interacts, plus any inactive identity keys they need for archiving purposes.

* Apps use secure channels when synchronizing ledgers. A ledger on a laptop and a phone thereby has two separate sets of keys, with each device's app holding the public keys of the other.

* One handshake sent by any of a sender's devices will trigger a refresh of the transport key/pre-shared key pairs on all applicable devices---the sender's for that recipient, and the recipient's for that sender. Moreover, devices might be out of sync and stay that way for any duration, so refreshed pairs might arrive long after the initial handshake, or never---hence the need to keep old pairs.

Apps MUST duplicate and propagate ledger secrets and pre-shared keys as needed to cluster ledgers that are held by more than one device. The Synchronization section lays this all out in detail, but in short: ledgers share PSKs across clusters, so that any device from a cluster can identify itself using the same PSK when interacting with other ledgers.

Apps MUST create a master key to authenticate users on app open. Apps MUST use that master key to encrypt the app's data so it's decrypted when at rest, and MUST NOT store decrypted data anywhere except as needed to run the app in the device's RAM. Apps MUST store this master key using a hardware enclave (if one is available) or the OS keychain. Note in passing that hardware enclaves don't all work the same. Some of them renege on the widely understood promise of not allowing secrets to leave the enclave outright. All but Android do that at the time of writing when using post-quantum keys, in fact---and even then, Android only keeps that promise for signing keys.

Apps MAY store the public keys of other ledgers for any duration, and MUST store those of a ledger's active counterparties.

Lastly, apps MUST NOT log secret keys of any kind, whether asymmetric, shared, or otherwise.


## Identifiers

These specifications use collision-resistant IDs, or IDs for short, to mean IDs that were generated using random or hash-based methods that ensure they are adequately collision-resistant.

Apps MAY encode collision-resistant IDs as they see fit when sharing them with other apps, but MUST share them as filename-, shell-, and URL-safe strings. In practical terms, this means characters MUST be drawn from the `[a-zA-Z0-9_.-]` alphabet. This ensures `base16`, `base58btc`, and other encodings are fine up to `base64url` with no `=` padding, while the likes of `base45`, which contains non-safe characters, are not. The `base58btc` encoding is RECOMMENDED.

These specifications use:

* Multihash of a non-JSON file or string to mean the raw, binary hash of its byte stream prefixed with a hash algorithm identifier and a length indicator encoded in a Multiformat-compatible format [@Multiformats].

* Multihash of a JSON file or string to mean the Multihash of its deterministic DAG-CBOR encoded byte stream representation (RFC 8949; @DagCBOR).

* Hashlink of a file, public key, or string to mean a standard W3C Hashlink [@W3C-Hashlink] without its `hl` scheme: the byte stream's multihash encoded with a Multiformat-compatible Multibase prefix, like `z` for `base58btc`. This is for use as file and key identifiers inside contracts and gossip payloads (see Instructions and Gossip).

* Canonical hash algorithm to mean SHA-256. Apps MUST use the canonical hash algorithm when creating any hashlink. That is its main use in this protocol.

* Public key in `did:jwk` format to mean `did:jwk:<key>` where `<key>` is the `base64url`-encoded JSON Web Key (JWK; RFC 7517) representation of that public key, as defined by the `did:jwk` method specification [@DID-JWK]. This is for use inside UCAN authorizations.

* Signature in `varsig` format to mean a cryptographic signature encoded as a byte string in `varsig` v1-compatible format [@Varsig]. This is for use inside COSE envelopes and UCAN authorizations to avoid multiplying signature files.

* A public key's hash algorithm to mean the inherent hash function natively used by the primitive or its cryptographic family (for pre-hashing payloads before signing them, or internal transformations like the Fujisaki-Okamoto transform), with hybrid keys using the hash function of their primary or post-quantum component. For instance, SHA2-512 for Ed25519/X25519 and P-521, SHA-256 for P-256, SHA-384 for P-384, and SHAKE-256 with a 512-bit output length for Ed448/X448 and the ML-DSA and ML-KEM keys.

* A public key's 32-byte hash algorithm to mean its usual hash algorithm with its output truncated to its first (leftmost) 32 bytes. These 32-byte hashes are for use in transmissions (see Transmissions).

Vendors SHOULD revisit the choice of SHA-256 if a vulnerability is ever found in it that materially affects its ability to uniquely identify documents that are being gossiped (see Gossip). A hypothetical collision vulnerability would far more likely affect its use in key derivation rather than this protocol's use for it, so the odds of ever needing to change it are about zero. It would require supporting more than one hash option. These self-describing formats ensure hashlinks are self-documenting should that ever become necessary.

Note: DAG-CBOR integer-handling rules diverge in Javascript. Apps MUST encode numbers that have no fractional part and are within the standard integer range as CBOR integers (major type 0 or 1, like in Rust and Go), not floating-point numbers (major type 7, as sometimes happens in Javascript). In practical terms, be mindful of your Node.js library, and add unit tests with integers beyond JavaScript's `Number.MAX_SAFE_INTEGER`.


## Forensics

Apps MUST maintain an append-only log for their transaction history. This log MUST compute its next hash using the canonical hash (see Identifiers) based on the data being logged, its previous state, and the local timestamp according to the local wall clock (see Logging).

This transaction history is not intended to synchronize hashes much less full logs between ledgers, nor is it intended for any type of consensus automation. It does not even try to be those things.

Rather, it is an append-only record of locally timestamped events that arrive asynchronously on disparate devices whose clocks are likely out of sync and possibly tampered with. Anyone using this as forensic evidence SHOULD assume timestamps in this log are dubious. Events could get logged long after they've been sent, so not even local timestamps can be trusted, and no assumption can be made about the event order and hashes across replicas of the same ledger (see Synchronization).

What the log is intended to provide is a tamper-resistant record of the order in which _local_ events containing _non-local_ references get committed to the log. Put another way, ledgers exchange encrypted information about their state as they interact, and embed that information into their own future state. These entangled histories make rewriting a ledger's transaction history impossible without also rewriting that of nearby ledgers on the graph to cover it up.

This tamper-resistant evidence of consideration and intent makes transactions on this graph _far more_ enforceable than they'd be with a mere cryptographic signature, and the dispute resolution process (see Disputes) offers repudiation guarantees in case of private key misuse that a blockchain cannot match without Orwellian levels of control.

Fittingly, this tamper-resistance is socio-cryptographic rather than absolute. Consider a gaslighting attack, where an adversary coordinates rewrites around a node until it abdicates its own judgement to its context. The parallels with conformity and deference to authority are striking [@Asch1956; @Milgram1963]. We'll flesh out the link with cognition later.

These logs enable sequencing events without needing synchronized wall clocks, and defining topologies on the transaction graph. This ties into spacetime and causal set theory, but that discussion will wait too. What matters for our sake is that these logs have strong forensic value.

See Logging for the details on log formats and device synchronization.


## Wall Clocks

The unreliability of wall clocks may need stressing for non-technical readers. Computers use internal oscillators to track time and NTP servers (Network Time Protocol) as their external source of truth. A computer's wall clock could be tampered with, the reference server it's deferring to could be lying, and the routers in between them could be lying too. Adding insult to injury, NTP pools aren't secure, so your choices are trusting a secure but specific NTP provider (plague) or trusting that no one is inside your router (cholera).

Transaction participants set signature deadlines and authorization expirations all the same, so we need to mind wall clock usage in deadlines and delegated signatures (see Promises and `/sign` Authorizations). Not all wall clock checks are made equal, however, because some transactions are harder to reverse from the perspective of the graph.

Critical transactions add or revoke proofs, or assign an executable action to _any_ of its signers (see Instructions). The first allows adding or removing a ledger controller. The other, anything a script can do, so could trigger a wire transfer or a cryptocurrency transaction. Given the stakes, a fresh wall clock check when signing or verifying the signature of such transactions makes sense.

Non-critical transactions can be more lenient. Off-graph due diligence is still warranted before releasing, shipping, or clearing what needs to be, but the tradeoff tilts toward making ledgers work offline since the transaction itself can be disputed as fraudulent and reversed.

See Logging for the details on wall clock synchronization.


## Privacy

Apps MUST encrypt and sign communications with other apps except as needed to first establish a secure channel (see Transmissions).

Apps MUST authenticate ledger controllers (see Public Keys and Authentication) before granting them access to the data the app holds, whether for use inside it, or outside it using this protocol (see Gossip and Trust) or other APIs that grant access to that data, nominal or anonymized, as records or aggregates, for any purpose---analysis, audits, reporting, load balancing, anything.

Uncompromising transaction privacy is a simple matter of creating new ledgers. Fill them directly or through intermediaries so they look creditworthy (see Intermediaries), exactly like you'd fill or pay someone to fill a prepaid card. With this said, transactions usually need to be kept confidential rather than made anonymous, and creating a new ledger is overkill in that case.

Transaction confidentiality is a simple matter of having a payment intermediary pay the bill. This guarantees that the Trust protocol, which normally reveals a non-zero balance along with direction and magnitude hints to help consolidate debt loops, leaks nothing---since the intermediary consolidated the transaction at payment time. Apps SHOULD offer UI (a checkbox) to enable ledger controllers to mark some or all transactions as confidential and automate enforcing that an intermediary pay the transaction in full.

Vendors should adopt the mindset that the best way to not leak information---or worse, find it dumped in a data breach---is to not ask for it to begin with. As such, Apps SHOULD NOT require personally identifiable information beyond what's needed for permission control (see Authorizations) and what end-users volunteer inside the transactions themselves.


## Authentication

Conceptually, authentication has two models:

1. Trust on first use, like when someone tells you their name when you first meet, or when you manually trust an SSH host on your first login, or in our case when a ledger's controller might trust another ledger's identity when the two ledgers first interact.

2. Proof, like when someone vouches for you (friends introduce you to someone, trusted peers have signed your public key), or when you show you control known data (a private key, an email, a website, a phone number, a password, a device, a fingerprint, or more, with multi-factor authentication).

Our main concerns are: how can you tell that this ledger with a public key you don't know is not a malicious user, and what to do when end-users rotate keys, lose devices, or simply merge ledgers? Rephrased in real life terms, how would you prove you are you after changing your signature? Essentially, you'd show a paper with your new signature signed using an old signature, or line up people who will vouch for it as evidence. With this context out of the way:

Apps MUST accommodate end-users that create and merge ledgers as they see fit across the transaction graph, and MUST accommodate end-users that lose control of their proof methods. To that end, apps MUST:

1. Use the ledger's current identity key as its identity in transactions and in the transaction log (see Forensics).

2. Allow ledgers to sign an identity key with another as proof that the signing key endorses the signed key (see Signed Proofs). Note that endorsing can go in either or both directions (see Key Rotations and Synchronization). Because identity keys are unique to a ledger, endorsements enable merging ledgers on the same or different devices.

3. Identify ledgers by their identity cluster, which is the set of keys that have endorsed one another, directly or indirectly, in either direction, across any number of devices. Note that an identity cluster can have more than one active identity key (one per device, essentially).

4. Allow ledgers to associate their key with addresses that they control as API endpoints (url, email, other; see Address Proofs). These addresses MAY be tied to more than one ledger, so apps MUST NOT use them for authentication except as local sign-in methods (like a unique sign-in or recovery link sent to an email).

5. Allow ledgers to permanently repudiate proofs from a specified date. This is about the proof only. Apps MUST invalidate any identity cluster merges that occurred after the specified date, and MUST let end-users handle the fallout using disputes---in the same way you'd dispute fraudulent transactions one by one when your credit card gets closed.

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

Apps MUST issue and MUST accept only transaction signatures that are valid from the ledger's point of view. In other words, apps MUST use the ledger's identity key to sign transactions directly, or UCAN authorizations so delegated keys can sign transactions on its behalf. Apps MUST attach these UCAN authorizations for delegated signatures to be valid (see Envelopes).

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

Apps SHOULD be open-source and have a reproducible build process. The latter means the build process should always produce the exact same binary, despite temporary files or random values set at compile time and the like. This is so ledger controllers can check that their app is not malware or spyware.

The spyware angle may need expanding on. Dystopian amounts of trackers exist online (usage trackers, advertisements), offline (surveillance cameras, smart billboards), and at their intersection (bank cards, location pings, social media, chat bots). That data later goes into marketing (ad bidding, customer profiling), security (fraud or other misuse detection), or reporting (fancy charts) tools---or more recently, in systems that deliver humanless analyses, decisions, pre-crime alerts [@Hung2023], kill targets [@King2024], and other hellish slop. This is not preordained. It's the product of choices, and the principal one is engineers enabling jerks who nag for sex or just take it.

In that light, apps SHOULD assume no end-user wants their tracking, SHOULD NOT prompt end-users to opt in on first use, and SHOULD keep all diagnostics logs local until an end-user agrees to send relevant data after a crash.

Vendors should get into 30-minute calls with a half-dozen end-users every now and then instead. Ask what they use your app for, how they use it, and where it gets in their way. A half dozen is a sweet spot that will surface most issues. You'll get far more actionable information about your app and market than from tracking data. Then follow up. A delighted end-user sends referrals like their life depends on it.
