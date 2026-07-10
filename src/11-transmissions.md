# Transmissions

\epigraph{The content of any medium blinds us to the character of the medium.
}{Marshall McLuhan, Understanding Media (1964)}

The takaway for non-technical readers: Transmissions are deliberately designed to be infrastructure-independent and transport-agnostic. Transactions advance asynchronously, one step at a time---quickly on the public web, or slowly as ledger controllers interact offline.


## Endpoints

Transmission endpoints are functionally equivalent, in that payload formats are uniform and get encrypted as a matter of course (see below). A few differences between them do exist, however.


### Interactive and Non-Interactive Endpoints

These specifications distinguish between two types of transmission endpoints:

- Interactive endpoints are HTTP-like: the transmission sender gets a response from the recipient with a response code and message to signal that the payload was successfully processed or not, and a lack of response (due to a timeout, for instance) signals that it was not. Global and local URI/IP endpoints are interactive endpoint examples.

- Non-Interactive endpoints are fire-and-forget: the sender sends their payload without expecting any response. Most endpoints are non-interactive: email and phone notification, file-drops on public web folders, and social media posts are all examples.

The two are similar from the Gossip protocols' viewpoints, which is strictly push-based, without polling. The payload format is exactly the same. The only difference beyond speed is that apps know whether or not their request arrived, which enables better transmission queue management.

The Trust protocol only works with interactive endpoints.

Apps MUST return response codes and messages mapped after standard HTTP status codes for all interactive endpoints.


### Global and Local Endpoints

These specifications further distinguish between global and local endpoints:

- Global endpoints are routable over the public internet, like public URI/IP- and email-based endpoints.

- Local endpoints are not, like private URI/IP-based enpoints over a LAN or a private WAN, and promity-based endpoints like Bluetooth.

The two are functionally identical from a transmissions viewpoint. The only difference is that apps MUST NOT share local endpoints as address proofs (see Address Proofs). Apps MAY share any endpoint in bootstrap handles (see below).


### Endpoint Selection

As noted while discussing address proofs, end-users often enter addresses in their preferred communication order, so apps SHOULD monitor which they enter first, SHOULD allow them to reorder them, and SHOULD reflect their preferred ordering when communicating address proofs and bootstrap handles.

Conversely, apps SHOULD monitor the order they receive addresses in, and SHOULD factor that when selecting endpoints to send Gossip and Trust payloads to, with two caveats:

- Apps SHOULD prefer interactive endpoints over non-interactive ones, because it's better to know if a gossiped transmission was successful or not.

- Apps SHOULD prefer local endpoints, if any are available, over global ones, because why send a payload to a server on the public internet if the intended recipient has a phone on same local network?


### Revoked Endpoints

Apps MUST NOT send payloads to addresses they know are currently revoked.

Apps MUST track which endpoint they've sent which payload to, and SHOULD offer to re-queue any payload that was sent to a revoked address between when it was revoked and when the app learned it was. Idempotent responses ensure recipients will treat duplicate gossip as network noise.


### Required Endpoints

Apps MUST support sending payloads to and consuming payloads from interactive endpoints using the `http` or `https` scheme:

    @! John: did:key:z6MkCMyGw... <https://api.acme.com>

The `http` and `https` schemes are equivalent for all practical intents since payloads are encrypted either way. Supporting these schemes ensure apps can interact over LANs at minimum. The `http` scheme allows avoiding certificate warnings on the latter.


### Recommended Endpoints

Apps SHOULD support sending payloads to and consuming payloads from at least one non-interactive endpoint (which is at vendors' discretion):

    @! John: did:key:z6MkCMyGw... <mailto:john@acme.com>
    @! John: did:key:z6MkCMyGw... <tel:+1-123-456-7890>

Mobile apps SHOULD support both the `mailto` and `tel` schemes.

Non-mobile apps SHOULD support the `mailto` scheme.

Apps MUST allow optional formatting for phone numbers for human-readability.


### Optional Endpoints

Apps MAY support other endpoints as they see fit. They are innumerable, so what follows are only examples that warranted a few notes.

Bluetooth endpoints MUST use the `ble` scheme when shared in bootstrap handles (see below). L2CAP byte stream APIS don't manage payload boundaries much less payload responses, so apps MUST manage Bluetooth payload boundaries manually using a size header (see Payload Format), and MUST make Bluetooth endpoints behave like bidirectional file drop-like endpoints without response codes, with the endpoints reversing roles when streaming return frames.

Cloud-based web folders MUST be declared using their domain as the scheme and the unique handle as the locator:

    @! John: did:key:z6MkCMyGw... <drive.google.com:AbCdE...>

Private messages on social media MUST be declared using their URN or domain as the scheme and the unique handle as the locator (and apps MUST allow optional formatting of phone numbers for human-readability here too):

    @! John: did:key:z6MkCMyGw... <facebook.com:john> <x.com:john>
        <whatsapp:+1-123-456-7890> <tg:john> <matrix:john@acme.com>


### Custom Endpoints

Vendor prefixes are undesirable for schemes, since the only thing that matters is that the endpoint works. Apps can simply try interactive endpoints to decide if they work or not, and will already try a different endpoint when one keeps failing. Non-interactive endpoints usually have stable APIs to avoid developer uproar, so any reasonably well tested implementation will do.


## Bootstrap Handles

Apps MUST support emitting, recognizing, and processing unencrypted bootstrap handles so ledgers can discover each other's public keys and API endpoints.

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


## Secure Channels

Apps MUST treat all channels as insecure for Gossip and Trust purposes---even HTTPS. TLS (RFC 8446) is the only practical option to create secure channels inside browsers, on corporate networks, or on captive portal WiFi networks. It provides strong security, but it uses centralized certificate authorities that could be compromised. Using EDHOC (RFC 9528) would make sense in the scenarios where it works, but the maintenance burden of offering it for those does not. Using TLS for other purposes (see Wall Clocks) is a necessary compromise.

Apps MUST use HPKE (RFC 9180) to seal messages for the recipient's ledger key when transmitting Gossip and Trust payloads. Apps MUST use HPKE _Base Mode_ so recipients can always decrypt messages and senders don't leak information about themselves in transport headers. It ensures an ephemeral key gets generated for each message. Senders will get authenticated via their signature (see Gossip, Trust, and Envelopes). The HPKE `info` parameter MUST contain raw bytes of the recipient's ledger key so the payload is contextually bound to it.


## Fingerprints

Fingerprints are relationally salted tokens designed to identify payloads sent by known counterparties without revealing their ledger key to observers.

Conceptually, fingerprints are like Truncated Key Identifiers, with the twists that the payload is based on the public key pair and the transmission channel that ledgers are interacting on instead of one key, and the hash algorithm is derived from the recipient's public key.

To compute a recipient's fingerprint, a sender's app MUST compute:

    Hash(<RecipientKey> || Hash(<SenderKey> || Hash(<RecipientAddress>)))

Where:

1. `<RecipientKey>` and `<SenderKey>` are the recipient's and the sender's raw public key bytes without Multicodec prefixes.

2. `<RecipientAddress>` means the recipient's address scheme and locator exactly like the recipient shared them with the sender, as raw UTF-8 bytes (in other words, preserve the case, and ignore address proof arguments; see Bootstrap Handles and Address Proofs).

3. `||` means concatenating raw bytes as is.

4. Hash is the algorithm derived from the recipient's ledger key. The codec in the key's `did:key` format reveals its type, which allows to deterministically map that key to the hash algorithm it uses for signing (see Curve Selection). P-256, P-384. and Ed25519 use SHA-256, SHA384, and SHA-512 respectively.

Apps MUST precompute, store, and index the first four bytes (leftmost) of all counterparty fingerprints for fast look-up. Four bytes are enough to guarantee that few if any collisions inside a set will exist, and allow an index layout optimization in database engines that offer Hash indexes.

Apps MUST NOT store the full fingerprint, as this would invite data breaches as a quick way to build a rainbow table.

Fingerprints allow an encrypted payload's recipient to determine its sender without trying every public key until they find one that works (see Payload Format), and enable ledgers to ask each other about the creditworthiness of a ledger without revealing its identity to those who don't know it (see Trust). In both cases, a simple look-up reduces the search space to a set small enough (typically one candidate key, rarely more) that recomputing the hash of each candidate key is perfectly acceptable.

Apps MUST compute new fingerprints when they learn about new or rotated keys.

Apps MUST temporarily retain old hashes when rotating keys (see Key Rotations), and MUST compute each counterparty's new fingerprint _before_ letting them know about the key rotation.


## Payload Format

The Gossip and Trust protocols (see Gossip and Trust) minimize interactions by batching payloads. Both treat batched payloads as atomic units of transmission and assume the transport will just work.

Apps MUST envelope batched payloads in flat CBOR maps (RFC 8949) that omit their optional self-describing tag. The exact Gossip and Trust payloads are different and detailed below.

These envelope formats pack the information needed to check the integrity of payloads before processing, without embedding predictable meta-information like MIME file headers or zip magic numbers or CBOR self-describing tags that could be used as a plaintext oracle or crib during cryptanalysis of the payload.

Apps MUST encrypt this CBOR map using HPKE (see Secure Channels).

Apps MUST wireframe this encrypted payload by adding the first 4 bytes of the sender's fingerprint for that transmission channel (see Fingerprints), so the payload's recipient can zero in on how to decrypt the payload without trying every key:

    [ 4-Byte Fingerprint ] [ HPKE Ciphertext ]

The fingerprint's high entropy and position make it look like encrypted data to a first time observer. In principle, it could be used as an oracle by analyzing traffic over time. In practice, the fingerprint is unique per counterparty pair and per transmission channel, and ledgers will have revealed their relationship to a traffic analyzer anyway. Plus, either counterparty can rotate their ledger key to change the fingerprint (see Key Rotations).

Most communication transports with be happy with this fingerprinted payload as is. Lower level ones, like Bluetooth L2CAP byte streams, need apps to manually communicate payload boundaries. In such cases, apps MUST add an extra 4-byte, big-endian unsigned integer header with the fingerprinted payload's byte size:

    [ 4-Byte Size ] [ 4-Byte Fingerprint ] [ HPKE Ciphertext ]

Apps that want to support exotic transports like radio-frequency-based ones may need to chunk payloads and handle the stream fragmentation and reassembly.


### Gossip Payloads

Gossip payload maps MUST correspond to a batch of files, with each file's key corresponding to its string-encoded Content Identifier (see Identifiers), and each value corresponding to an array containing the file's name followed its raw bytes:

    { <cid>: [<filename>, <bytes>], ... }

Each file MUST correspond to a contract, an envelope, or a contract attachment. Apps MUST check the integrity of the file recieved using the hashes encoded in the cids, and MUST request files to be re-issued when appropriate.

Apps SHOULD be mindful of file sizes when batching gossip payloads. Contracts and envelopes are always fair game to batch since they're small text files, but apps SHOULD NOT batch large contract attachments to inappropriate endpoints. In particular, apps SHOULD NOT batch attachments larger than what a typical mobile device can download in a second when gossiping by email, phone notification, or social media chat, to avoid needlessly draining batteries. Apps SHOULD instead gossip large files through an interactive endpoint at the earliest opportunity. Apps MAY offer UI to force sending a large attachment to override this default behavior.


### Trust Payloads

Trust request payload maps MUST be an envelope with three fields:

- `query`: contains the root `/score` authorization signed by the issuer, with optional `/sign` authorizations as required (see `/score` Authorizations and `/sign` Authorizations), each encrypted using a symmetric key.

- `chain`: contains `/score` authorizations signed by requesters as required, with optional `/sign` authorizations as required, to chain trust queries.

- `keys`: contains a map that pairs the fingerprints of the intended scorers with their respective copy of the symmetric key, encrypted for its intended scorer tied to that fingerprint using HPKE _Base Mode_. The `info` parameter MUST contain the raw bytes of the intended scorer's ledger key so the symmetric key is contextually bound to it.

    {
      "query": [ <encrypted_authorization>, ... ],
      "chain": [ <authorization>, ... ],
      "keys": { <fingerprint>: <encrypted_key>, ... }
    }

This setup maintains the privacy of the issuer being scored and allows peers to police abuses. Only the intended scorers know the fingerprints that the issuer uses to interact with them, so only they can decrypt the `/score` authorization in `query`. The latter scopes the request to an intended recipient, and limits it in time according to the scorer's wall clock (see Wall Clocks). Lastly, the public authorizations in `chain` ensures ledgers can authenticate every chained requester before chaining further, and police abuses as needed.

Trust response payload maps get batched as they arrive through chained streams, and MUST correspond to a batch of encrypted scores (see Trust Scores), with each key corresponding to the fingerprint of the score's assessor as it was passed in the request, and each value corresponding to the encrypted score of the request's original issuer, encrypted using HPKE _Base Mode_. The `info` parameter MUST contain the raw bytes of the intended recipient's ledger key so the symmetric key is contextually bound to it:

    { <fingerprint>: <encrypted_score>, ... }


### Steganography

Apps MAY encode wireframed payloads (see Payload Format) inside media files to overcome hostile transmission contexts.

Steganography is vendor-driven, but needs a mention because transport channels can face delivery problems. Corporate email gateways routinely block encrypted payloads they can't open and inspect, for instance. The workaround is to give corporate security your private key, but that is not always sane or practical.

On the flip side, steganography algorithms are many, not always maintained, and not always compatible for the same name (see `f5stegojs` and `F5Py`). So there is very little to latch onto except conventions on the address proof arguments to use (see Address Proofs).

Apps MUST reserve and recognize the `stego` address proof argument to signal a steganography requirement, and MUST NOT send payloads to that address if they cannot honor that steganography requirement. The `stego` argument MUST contain a case-insensitive steganography algorithm identifier. Any other argument used alongside it is vendor or algorithm specific.

Apps SHOULD namespace steganography identifiers behind a `vendor:<name>:` prefix to avoid collisions until enough vendors agree on the semantics. Heeding this suggestion will help avert the interoperability problems that plagued early internet browsers.

The goal here is getting past the email filter, not cryptographic obfuscation. If you're concerned about the latter, you shouldn't be using a fingerprint to know which ledger sent you a transaction. Also, local transports like WiFi or Bluetooth don't need steganography, since apps are communicating directly.


## Transmission Queues

Apps MUST maintain transmission queues for incoming and outgoing payloads. The Gossip and Trust sections cover the specific functionality needed for each one. 

Apps SHOULD follow transmission queue best practices---exponential back-off, jitter, failure thresholds, time-to-live, eviction, purging, etc. You know the drill if you've made it this far into this chapter.
