# Transmissions

\epigraph{The content of any medium blinds us to the character of the medium.
}{Marshall McLuhan, Understanding Media (1964)}


## Endpoints

Transmission endpoints are functionally equivalent in that they share a common payload format, but the underlying transport they use creates minor differences between them.


### Endpoint Types

These specifications distinguish between three endpoint types as follows:

* Interactive, HTTP-like endpoints, which have RESTful semantics. These qualify as interactive in that senders can tell their payload arrived from the response code or a lack thereof (due to a timeout), and recipients can infer it did from whether the socket flushed cleanly---without a broken pipe or connection error. Beyond HTTP endpoints themselves, CoAP endpoints (schemes `coap` and `coaps`) would be HTTP-like endpoints if any apps were to implement them.

* Interactive, stream-like endpoints, which have a bidirectional session where the sender and recipient switch roles as they send data to one another. These endpoints have no HTTP-like semantics, but senders can infer a payload arrived from whether the socket flushed cleanly. Bluetooth and NFC endpoints are both stream-like.

* Non-interactive, email-like endpoints, which are fire-and-forget. Senders can only tell their payload was sent successfully. Senders might get an error when it did not arrive, but not reliably enough that they can count on it. File drop endpoints are all email-like.

In addition, these specifications distinguish between global endpoints, which are routable over the internet (public HTTP, email), and local ones, which are not (HTTP over a LAN, Bluetooth). Apps MUST NOT share local endpoint addresses inside handshakes (see Handshakes).

These endpoints are all functionally equivalent. The slight differences between them tie into transmission queues and interaction flows. You know the identity key of the global HTTP endpoint you want to gossip a payload to, for instance, whereas you can't do anything useful with a local HTTP or NFC endpoint until the host tells you who it is. Beyond that, it's the exact same payload formats and responses, with gossip treating transmissions as blackboxes that just work (see Gossip).


### Endpoint Selection

End-users often enter addresses in their preferred communication order, so apps SHOULD monitor which they enter first, SHOULD allow them to reorder them, and SHOULD reflect their preferred ordering when communicating addresses.

Conversely, apps SHOULD monitor the order they receive addresses in, and SHOULD factor that in as a tie breaker when selecting endpoints to send payloads to.

Beyond that:

* Apps MUST prefer the interactive endpoint that is in use, if any; and

* Apps SHOULD prefer local endpoints when one is available; and

* Apps SHOULD prefer interactive endpoints over non-interactive ones.


### Revoked Endpoints

Apps MUST NOT send payloads to addresses they know are currently revoked.

Apps SHOULD flag for review any payloads they sent to a revoked address before they learned it had been revoked. Recipients treat duplicate gossip payloads as network noise, so there is no harm in re-sending them---but apps SHOULD let users decide whether to do so.


### Endpoint Discovery

Apps discover unknown endpoints:

* By scanning for endpoints that are being advertised on local networks (HTTP, Bluetooth), or connecting to them directly (NFC); or

* Through handles shared using QR codes, via NFC, and in contract files (see Handles).

* As `p2pledger:<address>` handles in other contexts, where `<address>` is a global HTTP or email endpoint address.

Apps MUST support consuming handles prefixed with the custom `p2pledger:` URI scheme.


### HTTP Endpoints

Apps MUST support HTTP endpoints, and MUST use the standard `https` and `http` schemes as applicable when sharing such endpoints in handles (see Handles):

    https://<global_address>
    http://<local_address>:<port>

Where:

* `<global_address>` is an HTTP endpoint with a Fully Qualified Domain Name (FQDN). Apps MUST NOT allow users to enter an IP address as an HTTP endpoint, MUST NOT expose UPnP IGD to end-users, and MUST ignore HTTP endpoints passed using a non-local IP address. The FQDN requirement is intended as a static IP address guarantee to spare users and vendors a lot of UPnP IGD-related misery. (Power users that use UPnP IGD with a domain name seldom need support.) Apps MUST use secure `https` with global endpoints.

* `<local_address>` is an IP address broadcast via mDNS / DNS-SD / Bonjour or shared in a QR code or via NFC (see Checkouts). Apps MUST use plain `http` with local HTTP endpoints to avoid certificate warnings.

* `<port>` is a port number. Apps MAY use the port 0 trick to let the operating system assign a random port number.

To send a payload as a request or a response to an HTTP endpoint, apps MUST:

0. Disable response buffering if applicable, to be able to catch broken pipe and connection errors.

1. Set the `Content-Type` header to `Content-Type: application/octet-stream`.

2. Set the `Content-Length` header to the wire-formatted payload's byte length (see Wire Format).

3. Start the body at byte offset `0`.

4. Output the raw bytes of the wire-formatted payload, without form field names.

5. Await a successful flush before marking the payload as sent.

Apps MUST send HTTP POST requests.

Host apps MAY piggyback on the open HTTP connection to return an HTTP response after successfully receiving an HTTP request.

Host apps MAY chunk HTTP responses by setting an initial `Content-Type` header to `Content-Type: multipart/mixed; boundary=<boundary>` and flushing payloads one at a time to catch partial deliveries in that case. This enables a host to send more than one payload in response to a single request, without requiring either side to hold onto session-related state.

Apps MUST limit HTTP response codes to exactly two:

* 403 (Forbidden), when closing the channel early. An attacker would know their payload got rejected because the connection got closed early, so a 403 does not reveal anything new or useful.

* 200 (OK), to signal that the payload arrived, whether it was accepted or not.

Apps MUST output a handle upon receiving an empty POST request to their HTTP or HTTPS endpoint. This allows initiating handshakes via HTTP.

Client apps MUST set the `<session_secret>` that their host shared in a QR code or via NFC as a `P2PLedger-Session: <session_secret>` header with an empty HTTP POST to retrieve their session (use the raw string value, without quotes). Host apps MUST output a handle with the session data upon receiving the latter.

Apps MUST use the service type `_p2pledger._tcp` when advertising their local HTTP endpoints via mDNS / DNS-SD / Bonjour, and MUST register them using their local endpoint's `<local_address>` and `<port>`.


### Bluetooth Endpoints

Apps SHOULD support Bluetooth endpoints on applicable devices, and MUST use the standard `ble` scheme when sharing such endpoints in handles (see Handles):

    ble:<service_uuid>:<le_psm>

Where:

* `<service_uuid>` is the service identifier. Host apps MUST set its value to the p2pledger-specific service identifier or to an ephemeral 128-bit UUID that they obtained to host a client's checkout session (see Checkouts).

* `<le_psm>` is an arbitrary low energy protocol/service multiplexer allocated by the operating system at runtime.

L2CAP Connection-Oriented Channels (CoC) are the Bluetooth equivalent of raw socket streams, but without payload boundary management. Apps MUST therefore use the predefined length header when using Bluetooth (see Wire Format).

Apps MUST await a successful flush before marking Bluetooth payloads as sent.

Host apps MUST output a handle when a client connects to its p2pledger-specific service identifier. This allows initiating handshakes via Bluetooth.

Host apps MUST output nothing when a client connects to an ephemeral service identifier, and MUST instead wait for a reasonable duration for the client to retrieve their session. Client apps MUST send the `<session_secret>` that their host shared using a QR code or via NFC as a payload to retrieve their session. Host apps MUST output a handle with the session data upon receiving the latter.

The p2pledger-specific service identifier enables initiating handshakes to pair devices (see Endpoint Discovery). Apps MUST derive it using a standard UUIDv5 library, the `Namespace_DNS` constant defined in RFC 9562 or its later version, whose value is `6ba7b810-9dad-11d1-80b4-00c04fd430c8` at the time of writing, and the `p2pledger.local` domain name:

    Service_UUID = UUIDv5(Namespace_DNS, "p2pledger.local")

The latter formula yields `2b88bd30-24ef-514c-9500-f62295979bfa`.


### NFC Endpoints

Apps SHOULD support Near-Field Communications (NFC) endpoints on applicable devices. NFC needs some discussion, because at the time of writing:

* Android supports Host-based Card Emulation (HCE) Type 4 Tags, which can mimic payment cards directly. iOS exposes card emulation via the iOS 18.1+ NFC & SE Platform Entitlement, which requires a security audit and paying a fee. From there, apps can run their ISO 7816-compliant Java Card Applet that implements this protocol inside the secure element.

* Android and iOS both expose NFC reader APIs. Note that traditional app roles (which these specifications use in what follows) are flipped in NFC: host apps (NFC readers) are open and active, and process the transactions of client apps (NFC Type 4 tags) that may or may not be open.

* Practical speeds are slower than the theoretical 424 kbps or higher of modern devices, because NFC processes waste most of their time waiting for 255-byte long chunks to get scheduled by the OS---one chunk at a time, with a pause in between each one.

* Transmissions are better sent and received as Application Protocol Data Unit (APDU) byte streams to avoid signaling overhead that would make NFC even slower and OS-level interference. APDU APIs are as low-level as they get, and require payload chunking and reconstruction for anything larger than 255 bytes.

In a typical card payment, NFC readers drive contactless NFC interactions. The reader asks the card what it can do. The card returns a list of Application Identifiers (AIDs). The reader picks one. The card tells it what it needs. The reader gives it the details (typically amount, currency, timestamp, and nonce). The card tells it how to get its card details. The reader then asks for them, and wraps things up by asking for a signed payload.

Mobile host apps initiate that process. Typically, the host will see the client taking their phone out, so will anticipate needing NFC or a QR code---the host hits a button that enables both on their terminal and shows the order's details and an invitation to tap their device with the screen oriented so the customer can review them. The host will necessarily have asked if this is a card payment or not at this point, since it would require using the card terminal or another app. Alternatively, the host will ignore all this and hit a pair device button. Either way, host apps MUST select this protocol's AID as their initial command.

Apps MUST register themselves as a handler for the Application Identifier (AID) `F05032504C6564676572`---which corresponds to the `0xF0` proprietary AID prefix followed by the `P2PLedger` ASCII sequence---and use it for this protocol.

Mobile client apps kick in upon receiving the host app's first command: the OS opens the app's background NFC handler and lets it handle the request---without unlocking, if using biometric identification. Apps MUST require authentication if the OS doesn't as a matter of course.

The client app MUST respond with a 90 00 (Success) response once open, and the usual protocol checkout flow proceeds with a twist.

The twist is that NFC is too slow to transfer anything more than a handle and a *small* signature envelope in under 300 ms---which is as long as typical users can hold a device still before shaky hands start creating connection problems or concerns about what's taking so long kick in.

With this in mind, host apps MUST send a handle (see Handles) as a raw binary APDU with the same data as a QR code, plus the session's data if applicable.

Client apps with a pre-established secure channel with their host app might end up with a contract that is beneath the ledger controller's maximum NFC expense threshold. Apps MUST sign such contracts automatically, because the NFC tap is proof of intent enough.

Client apps MUST, if this contract's signature envelope is under 1 kB in size, gossip the signature envelope (and only that) in the usual wire format as a raw binary APDU. Host apps MUST emit the NFC beep upon signing their own copy if it passed due diligence (raise an invalid payment error if not), but MUST NOT send it via NFC---host apps MUST gossip that receipt using another channel.

Client apps MUST fall back to using one of the endpoints listed in the handle, after sending an APDU with the standard 69 85 Conditions of Use Not Satisfied code to terminate the NFC interaction, in any other scenario.

The 1 kB size limit deliberately rules out sending ML-DSA signatures. Vendors SHOULD coordinate to increase this limit when NFC becomes able to comfortably gossip an ML-DSA signed signature envelope.

Apps MUST await a successful flush before marking NFC payloads as sent.


### Email Endpoints

Apps SHOULD support email endpoints, and MUST use the standard `mailto` scheme when sharing such endpoints in handles (see Handles):

    mailto:<user>+<tag>@<domain>

With the usual email `<user>`, `<tag>`, and `<domain>` semantics.

To send a payload to an email endpoint, apps MUST create a multipart email and add that payload as an attachment. Apps MUST attach at most one payload per email.

Apps MUST await a successful submission acknowledgment before marking email payloads as sent.

Apps MUST add an email subaddress (the `<tag>` in `<user>+<tag>@<domain>`) when the ledger controller forgets to add one, and SHOULD create a filter that moves emails with that subaddress to a dedicated folder automatically. This ensures ledger controllers can keep using their email address normally. Apps SHOULD NOT use `+p2pledger` or anything based on their app's name for this, since it would be a dead giveaway used as a tracking beacon. (Use a random dictionary word in the ledger controller's language, for instance.)

Email servers sometimes (though not always) send delivery error messages. Apps SHOULD catch such error messages by scanning for the email subaddress they are tracking, SHOULD ignore the offending addresses until the next handshake, and SHOULD ignore serial offenders permanently.

Apps MUST output a handle when the email subaddress they're tracking receives an email with no payload attached. This allows initiating handshakes via email.

Client apps MUST set the `<session_secret>` that their host shared in a QR code or via NFC as the first line of the email body to retrieve their session. Host apps MUST output a handle with the session data upon receiving the latter.

Note that email clients and servers might block or flag emails with no subject and no content as suspicious---particularly handshake emails with no attachment either. Apps SHOULD therefore set a subject and a body.

Also note that email endpoints use an unencrypted channel that leaks metadata. Apps SHOULD be wary of revealing anything useful about what's in the payload in the email's subject or body. Apps MAY use a *local* LLM to generate an email. (Have it write a fictional story one paragraph at a time, for instance.)

Apps MAY offer an option to keep emails with payloads stored on the server as an automated backup, and SHOULD otherwise delete emails after processing.

Note that corporate email gateways tend to silently drop emails that contain encrypted payloads they cannot inspect. Vendors that want to work around the latter SHOULD coordinate and define custom schemes to standardize how to embed payloads inside media files. (Steganography libraries have too many shortfalls at the time of writing, but the field is evolving quickly.)


### File Drop Endpoints

The early fanfare about IPv6 was that it would once again allow two devices to connect directly. NAT was viewed at the time as a hacky workaround to not run out of 32-bit IPv4 addresses. The accidental security NAT provided soon became a feature---you don't want botnets port scanning mobile phones or apps draining phone batteries flat by waking them up constantly.

Carriers are still dropping unsolicited inbound connections decades later, and will do so indefinitely. This comes on top of restrictive firewalls and mobile operating systems that shut down sockets.

True global peer-to-peer transport options are non-existent as a result. Every option depends on a relay to establish a connection, and every option depends on a mailbox to deliver payloads when two mobile apps are not in use at exactly the same time. Every option is re-inventing email with a twist. These endpoints are thus all non-interactive and fire-and-forget for our purpose.

This protocol is able to accommodate incompatible takes on how they work to a large degree, so there is little point in elaborating on any of them in detail. RESTful endpoints typically have stable APIs to avoid developer uproar, so any well-tested implementation will work. Apps can simply try the odd stream-like ones, and ignore those that don't as dysfunctional until the next handshake or another random event. What matters for interoperability is that endpoints can interact, so vendor-prefixing of schemes is OPTIONAL.

With this said, three rules are needed to avoid scattering schemes:

1. Apps MUST replace dots (`.`) with dashes (`-`) inside schemes derived from domain names, and MUST NOT use custom schemes with dots. RFC 3986 technically allows dots in URI schemes, but support outside of OS-level parsing and app routing is scarce due to fragile regular expressions and the abuse of custom schemes in phishing scams. Contracts get rendered outside of apps (see Contract Files), so dots in URI schemes are best avoided.

2. Cloud-based web folders SHOULD be declared using their domain as the scheme, and the unique handle as the locator:

        <scheme>:<handle>
        drive-google-com:AbCdE...

3. Social media channels and other social drop sites SHOULD be declared using their standard scheme if one exists, or using their domain as the scheme when not, and the valid handle (in any valid format) as the locator:

        <scheme>:<handle>
        facebook-com:john
        x-com:john
        whatsapp:+1-123-456-7890
        tg:john
        matrix:@john:acme.com
        matrix:u/john:acme.com
        nostr:npub180cvv07...
        nostr:john@acme.com

Apps MUST support optional formatting of phone numbers for human-readability. Storing them in E.164 format is fine.

Apps MUST NOT exceed the payload sizes specific to the file drop endpoint being used (such as the 128 kB size limit on most Nostr relays). Too large files can always wait until the next interaction.

The API semantics will depend on the exact endpoint. APIs are usually RESTful, and thus HTTP-like, if with a drop point. WebRTC and local radio-based meshes are stream-like for their interactive half, but delivering payloads to mobile devices that can't reliably wake up and open a socket depends on a drop point.

Endpoints SHOULD catch delivery error messages when applicable and handle them the same way email endpoints do: ignore the offending addresses until the next handshake, and ignore serial offenders permanently.

Apps SHOULD NOT add handle output semantics to file drop endpoints. Few of them are able to accommodate receiving no payload or a zero-length one anyway. Local endpoints cover in-person handshakes, and HTTP and email endpoints cover remote ones already.

Apps SHOULD NOT add session semantics to file drop endpoints. Local endpoints cover checkouts at store counters, and global HTTP endpoints cover the remote ones done by sharing a QR code by email or during a live stream.

Beyond that, apps MAY support file drop endpoints as they see fit.


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
