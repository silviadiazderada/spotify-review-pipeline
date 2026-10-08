"""Deterministic issue assignment (no model): issue = topic + subtopic, where the subtopic comes
from ordered keyword rules applied to the review text. The first matching rule wins; otherwise
the subtopic is "general". Changing these rules changes membership but needs no new model calls.

Version this file's rules with RULES_VERSION and rerun group + rank.
"""

import re

RULES_VERSION = "issues-v4"  # v2: checkpoint_500; v3: analysis_10000; v4 (2026-10-08): "add" verb no longer ads

# topic -> ordered list of (subtopic, regex). Patterns are case-insensitive.
RULES = {
    "billing": [
        ("premium_only_controls", r"\b(choose|chose|pick|select|specific|particular|certain)\b.{0,40}\b(song|track|music)|"
                                  r"\bskips?\b|\bskipping\b|\bshuffle\b|\bon.?demand\b|\brepeat\b|\brewind\b|"
                                  r"\bprevious\b|\bback\b.{0,15}\bsong|\bcan'?t (even )?play (the|a|any|my)\b|"
                                  r"\b(song|music|songs)\b.{0,15}\b(we|you|i|user'?s?)\b.{0,10}\b(want|like|choice)|"
                                  r"\bpart of the song|\baccording to\b.{0,15}\bchoice"),
        ("plan_purchase_activation", r"\bcan'?t'?\s*(buy|sign ?up|purchase|subscribe)|\bfamily\b|\bduo\b|\bstudent\b|"
                                     r"\btrial\b|\bactivat"),
        ("charges_refunds", r"\bcharg|\brefund|\bbilled|\bbilling\b|\bdeduct|\bpayment|\bcard\b|\bunauthori|\bscam|"
                            r"\bcancel\w*\b.{0,30}\b(sub|still|account|money)|\btook my money|\bstill (taking|hitting|paying)"),
        ("price", r"\bpric|\bexpensive|\bcost|\bafford|\bincrease|\bcheap|\bmoney\b|\$|\brs\.?\b|\brupee|\bdollars?\b|"
                  r"\bper month|\bevery month"),
        ("basic_features_paywalled", r"\bbasic\b|\beverything\b.{0,30}\b(premium|paid)|\bforc\w*\b.{0,30}\b(pay|buy|premium|purchase)|"
                                     r"\bwithout (premium|prime)|\bpremium (feature|pack|option|only|users?)|"
                                     r"\b(try|join|rejoin|get|buy|purchase|upgrade to|having) (spotify )?pr[ei]?m|\bpaying to use|"
                                     r"\b(is|are) (now )?(a )?premium|\bpay (for|to)\b|\bfree\b|\bonly for pr|\bno premium|"
                                     r"\bmain features|\bsubscriptions?\b|\bpr[ei]m\w*um"),
    ],
    "usability": [
        # v4: playlist/library additions first, so the verb "add" never lands in the ads issue.
        ("autoplay_unwanted", r"\bautoplay|\bauto-?play|\bautomatically (start|play|add)|"
                              r"\badd(s|ed|ing)?\b[^.!?]{0,30}\bto (my|the|your|our)?\s*(playlist|library|liked|queue)|"
                              r"\badd(s|ed|ing)? (random|different|other|unwanted|new|\d+) (songs?|music|tracks?)"),
        # v4: "ads"/"ad" and repeated-letter misspellings ("adds", "adddssss"); a bare "add" (verb) is not an ad.
        ("ads", r"\bads?\b|\badd+s+\b|\baddd+\b|\badvert|\bcomm?ercial|\babs\b|\bwerbung|\bpublicit|\banuncio|"
                r"விளம்பர|\biklan"),

        ("shuffle_skip_limits", r"\bshuffl|\bskips?\b|\bskipping\b|\brepeat\b|\bdifferent (song|artist)|\bnever heard|"
                                r"\bsame songs?\b|\brandom songs?|\bin order\b|\b(music|song)\b.{0,15}\b(we|you|i)\b.{0,10}\bwant|"
                                r"\bdidn'?t (select|choose|pick)|\b(does|plays?) (a |an )?(another|other) song"),
        ("redesign_ui", r"\bupdate|\bnew (design|layout|ui|look|interface|version)|\binterface\b|\blayout\b|"
                        r"\bhome ?(screen|page)\b|\bui\b|\bdesign\b|\bchang(ed|ing|e)\b|\bformat\b|\bugly\b|\bdisappeared\b"),
        ("library_playlists_queue", r"\bqueue|\bplaylist|\blibrary\b|\bsort|\bliked songs\b|\bfolder|\bnext\b"),
        ("controls_widgets", r"\bbutton|\bwidget|\block ?screen|\bnotification|\bcontrols?\b|\bswipe|\bscroll"),
    ],
    "playback": [
        ("crashes_wont_open", r"\bcrash|\bclos(e|es|ing)\b|\bshut|\bfreez|\bstuck|\bblack screen|\bwon'?t open|"
                              r"\bnot open|\bdoesn'?t open|\bkeeps? (closing|stopping)|\bcan'?t (even )?open|"
                              r"\b(does ?n[o']t|not|won'?t) load"),
        ("plays_wrong_songs", r"\b(another|different|random|inappropriate|wrong) song|\bautomatically play|"
                              r"\bplays? (a )?(completely )?(different|another)|\bfar away"),
        ("wont_play", r"\b(not|n'?t|never)\b.{0,15}\b(play|playing|listen|hear)|\bstopped letting me play|\bdoes ?not play|"
                      r"\bonly hear|\bonly play"),
        ("errors_glitches", r"\berror|\bwent wrong|\bglitch|\bstopped working|\bnot working|\bdoesn'?t work|\bbug"),
        ("devices_connect", r"\bcar\b|\bbluetooth|\bandroid auto|\bchromecast|\bconnect\b.{0,10}\b(device|speaker|tv)|"
                            r"\bspeaker|\bwatch\b|\bwear ?os|\btv\b|\balexa|\bgoogle assistant"),
        ("connection_offline", r"\binternet|\bnetwork|\bwi-?fi|\bno connection|\bconnection|\boffline|\bdata\b|\bonline\b|"
                               r"\bbuffer"),
        ("stops_pauses_skips", r"\bstops?\b|\bstopping|\bpaus|\bcuts? (off|out)|\binterrupt|\bskips? (by itself|randomly)|"
                               r"\bskipping"),
        ("audio_quality", r"\bsound|\baudio|\bquality|\bvolume|\bequali[sz]|\blag|\bhd\b|\bhi-?fi|\blossless|\bstutter"),
        ("battery_performance", r"\bbattery|\bslow|\bstorage|\bram\b|\bcache|\bheat"),
    ],
    "access": [
        ("logged_out", r"\blog(s|ged)? ?(me )?out|\blogout|\bsign(ed)? ?out"),
        ("phone_signup_account", r"\bphone number|\b(different|another) number|\bset ?up\b.{0,15}\baccount|\bsign ?up|"
                                 r"\bcreate\b.{0,15}\baccount|\bretrieve\b.{0,10}\baccount|\bgmail|\bfacebook"),
        ("login_password", r"\blog ?in\b|\blogin|\bsign ?in|\bpassword|\blogging in|\blet me in|\biniciar"),
        ("account_hacked_locked", r"\bhack|\blocked|\bbann|\bsuspend|\bverif|\bemail\b|\bcode\b|\bnot allowed"),
        ("region_unavailable", r"\bin (macau|indonesia|iran|china|russia|my country)|\bcountry|\bregion|\bvpn|"
                               r"\bnot available in"),
    ],
    "downloads": [
        ("downloads_disappear", r"\bdisappear|\bdeleted|\bgone\b|\blost\b|\bvanish|\bremov|\bre-?download"),
        ("offline_playback", r"\boffline"),
    ],
    "catalog": [
        ("lyrics", r"\blyric"),
        ("recommendations", r"\brecom+end|\bsuggest|\bdiscover|\balgorithm|\bdaily mix|\bradio\b|\bsmart shuffle|"
                            r"\brandomly adds"),
        ("search", r"\bsearch|\bcan'?t (even )?find|\blooking for|\bidentify"),
        ("podcasts_audiobooks", r"\bpodcast|\baudiobook|\bepisode|\bvideo"),
        ("missing_content", r"\bmissing|\bremov|\bnot available|\bunavailable|\bgr[ae]y(ed)?\b|\bnot all (music|songs)|"
                            r"\bdon'?t have|\bno longer|\bnot ave?a?i?ble|\blimited\b|\bdeleted|\bfaltando|\bnot show|"
                            r"\bnothing is showing|\bempty"),
    ],
    "support": [],
    "other": [],
}

_COMPILED = {t: [(s, re.compile(p, re.IGNORECASE)) for s, p in rules] for t, rules in RULES.items()}


def subtopic(topic, text):
    for name, pattern in _COMPILED.get(topic, []):
        if pattern.search(text or ""):
            return name
    return "general"


def issue_id(topic, sub):
    return f"ISS-{topic}-{sub}"
