# *Deutsch* &mdash; German (`de`)

This datasheet is for sps-corpus-4.0-2026-06-12 of the Mozilla Common Voice *Spontaneous Speech* dataset for German [Deutsch - `de`]. The dataset contains 319 clips representing 1.21 hours of recorded speech (0.2 hours validated) from 28 speakers.

## Data splits for modelling

The dataset clips are categorised by transcription status and training-set assignment. The following tables summarise the distribution.

### Audio clips

| Bucket | Clips | % |
| --- | --- | --- |
| Transcribed & Validated | 65 | 20.4% |
| Transcribed & Pending | 199 | 62.4% |
| Not transcribed | 55 | 17.2% |

### Training splits

| Bucket | Clips | % |
| --- | --- | --- |
| Train | 0 | 0.0% |
| Dev | 0 | 0.0% |
| Test | 0 | 0.0% |
| Unassigned | 319 | 100.0% |

Training split coverage: 0 of 65 transcribed & validated clips (0.0%)

## Transcriptions

### Transcription status

| Bucket | Clips | % |
| --- | --- | --- |
| Validated | 65 | 24.6% |
| Pending | 199 | 75.4% |
| Edited | 18 | 6.8% |

### Samples

#### Questions

There follows a randomly selected sample of questions used in the corpus.

1. *Wenn du ein Tier wärst, welches wärst du und warum?*
2. *Nutzen Sie in Ihrem Haus eine Biotonne?*
3. *Haben Sie bereits einen Chatbot genutzt? Wenn ja, für welches Thema?*
4. *Wohin fährst du am liebsten in den Urlaub?*
5. *Welche Traditionen pflegst du in deiner Familie?*

#### Responses

There follows a randomly selected sample of transcribed responses from the corpus.

1. *Ich arbeite in einem Büro und habe es mir angewöhnt abends nach zwanzig Uhr zirka ne Stunde lang spazieren zu gehen, währenddessen hör ich mir Podcasts an oder Hörbücher und ehm dadurch wenn ich wieder zuhause bin, bin ich ausgepowert und müde und gleichzeitig hab ich Bewegung gekriegt und eh nehme dadurch nicht zu.*
2. *Vermutlich meine Crooks, die haben jetzt schon 5 Jahre hinter sich.*
3. *Im daylie Buisness in Form meines Anwendungsentwicklers zur Unterstützung meiner ticken Systeme.*
4. *Ich mag sehr gerne Regen und zwar deswegen weil er einen dazu bringt drinnen zu bleiben und trotzdem was draußen präsent macht.*
5. *Ja das hab ich tatsächlich gemacht, sogar ziemlich am Anfang ah, der Grund dafür? Na ich wollt einfach mal schauen wie aktiv die Community ist, ich mein das kann man da am besten abschätzen. Und da kann man auch gut prüfen wie man selbst so seinen Beitrag leistet und wie man in Vergleich zu anderen steht. Ich find das sehr praktisch.*

### Fields

Each row of a `tsv` file represents a single audio clip, and contains the following information:

- `client_id` - hashed UUID of a given user
- `audio_id` - numeric id for audio file
- `audio_file` - audio file name
- `duration_ms` - duration of audio in milliseconds
- `prompt_id` - numeric id for prompt
- `prompt` - question for user
- `transcription` - transcription of the audio response
- `votes` - number of people that who approved a given transcript
- `age` - age of the speaker[^1]
- `gender` - gender of the speaker[^1]
- `language` - language name
- `split` - for data modelling, which subset of the data does this clip pertain to
- `char_per_sec` - how many characters of transcription per second of audio
- `quality_tags` - some automated assessment of the transcription--audio pair, separated by `|`
  - `transcription-length` - character per second under 3 characters per second
  - `speech-rate` - characters per second over 30 characters per second
  - `short-audio` - audio length under 2 seconds
  - `long-audio` - audio length over 5 minutes
  - `non-allowed-script` - transcription contains characters from a writing system not associated with the language
  - `mixed-script-words` - a single word contains characters from multiple writing systems
  - `mixed-script-transcription` - transcription spans multiple writing systems, but each word consistently uses only one

---

[^1]: For a full list of age, gender, and accent options, see the [demographics spec](https://github.com/common-voice/common-voice/blob/main/web/src/stores/demographics.ts). These will only be reported if the speaker opted in to provide that information.

## Get involved

### Community links

- [Common Voice translators on Pontoon](https://pontoon.mozilla.org/de/common-voice/contributors/)
- [Common Voice Communities](https://github.com/common-voice/common-voice/blob/main/docs/COMMUNITIES.md)

### Discussions

- [Common Voice on Matrix](https://chat.mozilla.org/#/room/#common-voice:mozilla.org)
- [Common Voice on Discourse](https://discourse.mozilla.org/t/about-common-voice-readme-first/17218)
- [Common Voice on Discord](https://discord.gg/9QTj9zwn)
- [Common Voice on Telegram](https://t.me/mozilla_common_voice)

### Contribute

- [Contribute questions](https://commonvoice.mozilla.org/spontaneous-speech/beta/question)
- [Validate questions](https://commonvoice.mozilla.org/spontaneous-speech/beta/validate)
- [Answer questions](https://commonvoice.mozilla.org/spontaneous-speech/beta/prompts)
- [Transcribe recordings](https://commonvoice.mozilla.org/spontaneous-speech/beta/transcribe)
- [Validate transcriptions](https://commonvoice.mozilla.org/spontaneous-speech/beta/check-transcript)

## Licence

This dataset is released under the [Creative Commons Zero (CC-0)](https://creativecommons.org/public-domain/cc0/) licence. By downloading this data you agree to not determine the identity of speakers in the dataset.
