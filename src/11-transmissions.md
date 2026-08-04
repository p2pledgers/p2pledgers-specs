# Transmissions

\epigraph{The content of any medium blinds us to the character of the medium.
}{Marshall McLuhan, Understanding Media (1964)}


## Endpoints

Transmission endpoints are functionally equivalent in that they share a common payload format, but the underlying transport they use create minor differences between them.


### Endpoint Types

These specifications distinguishes between interactive and non-interactive endpoints as follows:

* Interactive endpoints that are HTTP-like: The sender sends their payload and the recipient's response signals whether it arrived using a response code or a lack of response (due to a timeout), so there is no uncertainty about delivery failures. Conversely, the recipient can infer their response arrived based on whether the socket flushed cleanly---a broken pipe or another connection error wouold signal that it did noot. HTTP endpoints are HTTP-like, as would be CoAP if apps implement it.

* Interactive endpoints that are stream-like: The sender and the recipient open a bidirectional session and switch roles as they send data to one another. The sender gets no HTTP-like response, but can infer their payload arrived based on whether it got flushed without any connection errors. Stream-like endpoints can require senders and recipients to manage payload boundaries manually. Apps MUST use the predefined length header in such cases (see Wire Format). Bluetooth and NFC endpoints are stream-like, as would be WebRTC if apps implement it.

* Non-interactive endpoints that are email-like: The sender sends their payload and knows only it was sent. The sender sometimes gets an error when it did not, but not reliably enough that they can count on it. Endpoints SHOULD manage such error messages. Email is a non-interactive endpoint, as would be files dropped in public web folders or sent through social media if apps implement those.

In addition, these specifications distinguish between global endpoints, which are routable over the internet (public HTTP, email), and local ones, which are not (HTTP over a LAN, Bluetooth). Apps MUST NOT share local endpoint addresses inside contracts (see Address Proofs).

These endpoints are all functionally equivalent. The slight differences between them tie into transmission queues and interaction flows. You know the identity key of the global HTTP endpoint you want to gossip a payload to, for instance, whereas you can't do anything useful with a local HTTP or NFC endpoint until the host tells you who it is. Beyond that, it's the exact same payload formats and responses, with gossip treating transmissions as blackboxes that just work (see Gossip).


### Endpoint Selection

End-users often enter addresses in their preferred communication order, so apps SHOULD monitor which they enter first, SHOULD allow them to reorder them, and SHOULD reflect their preferred ordering when communicating addresses.

Conversely, apps SHOULD monitor the order they receive addresses in, and SHOULD factor that in when selecting endpoints to send payloads to, with two caveats:

* Apps SHOULD prefer local endpoints when one is available; and

* Apps SHOULD prefer interactive endpoints over non-interactive ones.


### Revoked Endpoints

Apps MUST NOT send payloads to addresses they know are currently revoked.

Apps SHOULD flag for review any payloads they sent to a revoked address before they learned it had been revoked. Recipients treat duplicate gossip payloads as network noise, so there is no harm in re-sending them---but apps SHOULD let users decide whether to do so.


### HTTP Endpoints

Apps MUST support http endpoints, and MUST use the standard `https` or `http` schemes as applicable when sharing such endpoints in handles (see Handles):

    https://api.acme.com
    http://<local_ipaddr>:<port>

The `http` and `https` schemes are equivalent for all practical intents since payloads are encrypted either way. Supporting these schemes ensures apps can interact over LANs, and thus guarantees a minimum level of interoperability.

Apps SHOULD use `http` with local addresses to avoid certificate warnings.

To send a payload as a request or a response to an HTTP endpoint, apps MUST:

0. Disable response buffering if applicable, to be able to catch broken pipe and connection errors.

1. Set the `Content-Type` header to `Content-Type: application/octet-stream`.

2. Set the `Content-Length` header to the wire-formatted payload's byte length  (see Wire Format).

3. Start the body at byte offset `0`.

4. Output the raw bytes of the wire-formatted payload, without form field names.

5. Await a successful flush before marking the payload as sent.

Apps MAY chunk HTTP requests and responses by setting an initial `Content-Type` header to `Content-Type: multipart/mixed; boundary=<boundary>`. Apps MUST flush payloads one at a time to catch partial deliveries in that case.

Apps MUST use HTTP POST to send requests.

Apps MUST limit HTTP response codes to exactly two:

* 403 (Forbidden), when closing the channel early. An attacker would know their payload got rejected because the connection got closed early, so a 403 does not reveal anything new or useful.

* 200 (Ok), to signal that the payload arrived, whether it was accepted or not.

Apps MAY piggyback on an open HTTP connection to return an HTTP response after successfully receiving an HTTP request.


### Bluetooth Endpoints

Apps SHOULD support Bluetooth endpoints on applicable devices, and MUST use the standard `ble` scheme when sharing such endpoints in handles (see Handles):

    ble:<p2pledger_uuid>:<le_psm>

Where:

* `p2pledger_uuid` is the p2pledger-specific service identifier, which is the Bluetooth equivalent of a domain name (so apps don't waste battery interacting with random smart-bulbs); and

* `le_psm` is an arbitrary low energy protocol/service multiplexer allocated by the operating system at runtime, which is the Bluetooth equivalent of a random TCP/IP port number.

Apps MUST derive the p2pledger-specific service identifier using a standard UUIDv5 library, the `Namespace_DNS` constant defined in RFC 9562 or its later version, whose value is `6ba7b810-9dad-11d1-80b4-00c04fd430c8` at the time of writing, and the `p2pledger.local` domain name:

    Service_UUID = UUIDv5(Namespace_DNS, "p2pledger.local")

The latter formula yields `2b88bd30-24ef-514c-9500-f62295979bfa`.

Note that Bluetooth UUIDs identify service types that devices recognize rather than individual devices, so the semantics differ slightly from other addresses. Devices share their human-readable names and addresses through advertising and scan response packets.

What is more, OS-allocated PSMs (in the range `0x0080–0x00FF`) are dynamic. A `ble:<p2pledger_uuid>:<le_psm>` handle in a QR code or an NFC tag is liable to go stale when its issuer opens another phone app. Apps SHOULD try to get a new PSM from `<p2pledger_uuid>` when an L2CAP connection fails or times out before giving up.

Beyond this, L2CAP Connection-Oriented Channels (CoC) are to Bluetooth what raw socket streams are to TCP/IP, but without any payload boundary management. Apps MUST therefore use the predefined length header when using Bluetooth L2CAP (see Wire Format).

Apps MUST await a successful flush before marking Bluetooth payloads as sent.


### NFC Endpoints

Apps SHOULD support Near-Field Communications (NFC) endpoints on applicable devices. NFC endpoints are an outlier because at the time of writing:

* Practical speeds are slower than the theorical 424 kbps or higher of modern devices, because NFC processes waste most of their time waiting for 255-byte long chunks to get scheduled by the OS---one chunk at a time, with a pause in between each one.

* The high-level NFC Data Exchange Format (NDEF), which abstracts away payload chunking, wraps payloads in envelopes that reduce the effective chunk size even further. Using NDEF when a client connects is needed to tell the OS to open the app or offer to download it.

* Transmissions beyond the first are better sent and received as Application Defined Protocol Unit (ADPU) byte streams to avoid the signaling overhead and OS-level interference. That API requires payload chunking and reconstruction for anything larger than 255 bytes.

In other words, exchanging anything other than handles and signatures by NFC is dead on arrival. Apps MUST instead limit NFC endpoint interactions to:

1. An initial NDEF message containing a universal link that opens or offers to download the app (see Universal Links), immediately followed by an ADPU message containing a handle, on client connect.

2. An ADPU client response containing the applicable signature envelope---and that only.

In practical terms, upon getting the NFC host's initial two messages:

* A client with a pre-established secure channel with the NFC host can end up with a contract that can be signed automatically (see Sessions). Apps MUST sign such contracts automatically (the NFC tap is proof of intent enough), and MUST send their signature envelope as a response in an ADPU message if the response is no larger than the host's capability container size.

* Apps MUST use one of the endpoints in the handle in any other scenario.

This ensures users don't need to hold their devices still for longer than 300 ms---which is as long as they typically can before shaky hands start creating connection problems. 

Note that apps MUST set a capability container size in the initial NDEF message sent as NFC host. This sets the maximum size that they'll accept as a response by the client. Apps SHOULD set this size to 1 kB. That will fit most signature envelopes with a few UCAN authorizations signed using a traditional curve-based identity key, and rules out sending large ML-DSA-based signatures that wouldn't fit in the target 300 ms time window anyway.

Apps MUST await a successful flush before marking NFC payloads as sent.

For the rest, only Android devices are able to emulate a Type 4 Tag at the time of writing. NFC hosting on iOS only enables authorizing bank card payments, and even that requires developers to jump through hoops. It follows that, whereas any device can serve as a client doing the tapping, only Android devices can serve as an NFC host being tapped.

Apps MUST NOT passively host an NFC endpoint to avoid data exposure risks. Apps MUST instead require users to start an NFC host and await a client's tap. This can be done automatically as part of a checkout, or manually as part of pairing devices (see Handshakes).


### Email Endpoints

Apps SHOULD support email endpoints, and MUST use the standard `mailto` scheme when sharing such endpoints in handles (see Handles):

    mailto:john@acme.com

To send a payload to an email endpoint, apps MUST create a multipart email and add that payload as an attachment. Apps MUST send one payload per email.

Apps MUST await a successful API response before marking email payloads as sent.

Email endpoints are intended to enable ledger controllers to review and sign contracts on the go while getting large attachments through higher bandwidth endpoints like HTTP or Bluetooth.

4G LTE networks are commonplace in the countryside at the time of writing, and will be for a while longer. In typical conditions, those offer 10-50 Mbps with a 40–80 ms latency for downloads, and 1-5 Mbps uploads with a 60-120 ms latency for uploads. Ignoring latency to some degree is sound since apps aren't sending and receiving payloads in the foreground, but not at the cost of making devices feel unresponsive because of ongoing uploads and downloads in the background.

For this reason, apps MUST limit what they send to and from email endpoints to contracts (always), signature envelopes (always), and small attachments (if and only if they fit), MUST NOT batch files that are 125 kB or larger (see Payload Format), and MUST keep total batch sizes to 125 kB at most before encryption. This limits payload sizes to something that a mobile device can realistically hope to upload in a second.

Apps MUST be mindful that email endpoints use an unencrypted channel that can leak metadata. Apps SHOULD NOT allow handshakes using email endpoints.


### Custom Endpoints

The only thing that matters for interoperability is that endpoints are able to interact. Vendor prefixes are thereby undesirable for schemes. Non-interactive endpoints often have stable APIs to avoid developer uproar, so any well-tested implementation will work. As to interactive endpoints, apps can just try using them to decide if they work and ignore them as dysfunctional when not (if only for a while). The protocol thus accommodates incompatible takes on how schemes work, with the details left at vendors' discretion.

With this said, three rules are needed to avoid scattering schemes:

1. Apps MUST replace dots (`.`) with dashes (`-`) inside schemes derived from domain names, and MUST NOT use custom schemes with dots. RFC 3986 technically allows dots in URI schemes, but support outside of OS-level parsing and app routing is scarce due to fragile regular expressions and the abuse of custom schemes in phishing scams. Contracts get rendered outside of apps (see Contract Files), so dots in URI schemes are best avoided.

2. Cloud-based web folders MUST be declared using their domain as the scheme, and the unique handle as the locator:

        @! John: did:key:z6MkCMyGw... <drive-google-com:AbCdE...>

3. Private messages on social media MUST be declared using their URN or domain as the scheme, and the unique handle as the locator:

    @! John: did:key:z6MkCMyGw... <facebook-com:john> <x-com:john>
        <whatsapp:+1-123-456-7890> <tg:john> <matrix:john@acme.com>

Apps MUST support optional formatting of phone numbers for human-readability.

Beyond that, apps MAY support other endpoints as they see fit.


## Fingerprints

Fingerprints are relationally salted tokens designed to identify payloads sent by known counterparties without revealing their ledger key to observers.

Conceptually, fingerprints are like Truncated Key Identifiers, with the twists that the payload is based on the public key pair and the transmission channel that ledgers are interacting on instead of one key, and the hash algorithm is derived from the recipient's public key.

To compute a recipient's fingerprint, a sender's app MUST compute:

    Hash(<RecipientKey> || Hash(<SenderKey> || Hash(<RecipientAddress>)))

Where:

1. `<RecipientKey>` and `<SenderKey>` are the recipient's and the sender's raw public key bytes without Multicodec prefixes.

2. `<RecipientAddress>` means the recipient's address scheme and locator exactly like the recipient shared them with the sender, as raw UTF-8 bytes (in other words, preserve the case, and ignore address proof arguments; see Bootstrap Handles and Address Proofs).

3. `||` means concatenating raw bytes as is.

4. Hash is the algorithm derived from the recipient's ledger key. The codec in the key's `did:key` format reveals its type, which allows to deterministically map that key to the hash algorithm it uses for signing (see Curve Selection). P-256, P-384. and Ed25519/X25519 use SHA-256, SHA384, and SHA-512 respectively.

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
