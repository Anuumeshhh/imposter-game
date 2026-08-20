import random
import base64

_ENCODED_DATA = [
    # Anime & Manga
    ("R29rdQ==", "VmVnZXRh"), ("TmFydXRvIFV6dW1ha2k=", "U2FzdWtlIFVjaGloYQ=="),
    ("TGlnaHQgWWFnYW1p", "TCBMYXdsaWV0"), ("RXJlbiBZZWFnZXI=", "UmVpbmVyIEJyYXVu"),
    ("U2FpdGFtYQ==", "R2Vub3M="), ("SWNoaWdvIEt1cm9zYWtp", "VXJ5dSBJc2hpZGE="),
    ("TWlkb3JpeWEgSXp1a3U=", "QmFrdWdvIEthdHN1a2k="), ("VGFuamlybyBLYW1hZG8=", "TmV6dWtvIEthbWFkbw=="),
    ("R29qbyBTYXRvcnU=", "UnlvbWVuIFN1a3VuYQ=="), ("THVmZnk=", "Um9yb25vYSBab3Jv"),
    ("QWxsIE1pZ2h0", "RW5kZWF2b3I="), ("RWR3YXJkIEVscmlj", "QWxwaG9uc2UgRWxyaWM="),
    ("R29uIEZyZWVjc3M=", "S2lsbHVhIFpvbGR5Y2s="), ("U3Bpa2UgU3BpZWdlbA==", "VmljaW91cw=="),
    ("WXVqaSBJdGFkb3Jp", "TWVndW1pIEZ1c2hpZ3Vybw=="), ("U2hvdG8gVG9kb3Jva2k=", "RGFiaQ=="),
    ("RGVtb24gU2xheWVy", "SGFzaGlyYQ=="), ("RGV2aWwgRnJ1aXQ=", "SGFraQ=="),
    ("Q2hha3Jh", "TmluanV0c3U="), ("RG9tYWluIEV4cGFuc2lvbg==", "Q3Vyc2VkIFRlY2huaXF1ZQ=="),
    ("QmFua2Fp", "U2hpa2Fp"), ("U3VwZXIgU2FpeWFu", "VWx0cmEgSW5zdGluY3Q="),
    ("U3VydmV5IENvcnBz", "R2Fycmlzb24gUmVnaW1lbnQ="), ("RGVhdGggTm90ZQ==", "U2hpbmlnYW1p"),
    ("VGl0YW4gU2hpZnRlcg==", "UHVyZSBUaXRhbg=="), ("UGhpbG9zb3BoZXIncyBTdG9uZQ==", "SHVtYW4gVHJhbnNtdXRhdGlvbg=="),
    ("U2hhZG93IENsb25l", "UmFzZW5nYW4="), ("TWF0ZXJpYQ==", "U3VtbW9u"),
    ("TmV6dWtv", "S2FuYW8="), ("S2lsbHVh", "S2lyYW8="),
    ("U2hpbnNla2Fp", "R3JhbmQgTGluZQ=="), ("T25lIFBpZWNl", "QWxsIEJsdWU="),
    ("S2lyaXRv", "QXN1bmE="), ("U3Vib3J1", "RW1pbGlh"),
    ("UmVt", "UmFt"), ("U2hpcm8=", "U29yYQ=="),
    ("S2FndXlh", "TWl5dXtp"), ("QW55YSBGb3JnZXI=", "TG9pZCBGb3JnZXI="),
    ("WW9yIEZvcmdlcg==", "Qm9uZCBGb3JnZXI="), ("S2VudGFybyBNaXVyYQ==", "R3V0cw=="),
    ("R3JpZmZpdGg=", "Q2FzY2E="), ("TWFraW1h", "RGVuamk="),
    ("UG9jaGl0YQ==", "UG93ZXI="), ("QWtpIEhheWFrYXdh", "SGltZW5v"),
    ("TW9i", "UmVpZ2Vu"), ("S2FpZW4=", "S3Vyb3Nha2k="),
    ("WW9ydWljaGk=", "S2lzdWtl"), ("SGl0c3VnYXlh", "TWF0c3Vtb3Rv"),

    # Gaming Legends & Factions
    ("QXJ0aHVyIE1vcmdhbg==", "Sm9obiBNYXJzdG9u"), ("S3JhdG9z", "QXRyZXVz"),
    ("R2VyYWx0IG9mIFJpdmlh", "WWVubmVmZXIgb2YgVmVuZ2VyYmVyZw=="), ("TWFzdGVyIENoaWVm", "QXJiaXRlcg=="),
    ("U29saWQgU25ha2U=", "TGlxdWlkIFNuYWtl"), ("TGluaw==", "WmVsZGE="),
    ("TWFyaW8=", "THVpZ2k="), ("Q2xvdWQgU3RyaWZl", "U2VwaGlyb3Ro"),
    ("TmF0aGFuIERyYWtl", "VmljdG9yIFN1bGxpdmFu"), ("Q29tbWFuZGVyIFNoZXBhcmQ=", "R2FycnVzIFZha2FyaWFu"),
    ("RWxsaWU=", "Sm9lbA=="), ("VHJldm9yIFBoaWxpcHM=", "TWljaGFlbCBEZSBTYW50YQ=="),
    ("U3RldmU=", "QWxleA=="), ("U2Fucw==", "UGFweXJ1cw=="),
    ("UGFjLU1hbg==", "Qmxpbmt5"), ("U29uaWMgdGhlIEhlZGdlaG9n", "U2hhZG93IHRoZSBIZWRnZWhvZw=="),
    ("RG9vbSBTbGF5ZXI=", "TWFyYXVkZXI="), ("QXNzYXNzaW5z", "VGVtcGxhcnM="),
    ("QWxsaWFuY2U=", "SG9yZGU="), ("SmVkaQ==", "U2l0aA=="),
    ("Q291bnRlci1UZXJyb3Jpc3Rz", "VGVycm9yaXN0cw=="), ("UmFkaWFudA==", "RGlyZQ=="),
    ("QXV0b2JvdHM=", "RGVjZXB0aWNvbnM="), ("T3ZlcndhdGNo", "VGFsb24="),
    ("U2NvdXJnZQ==", "U2VudGluZWw="), ("VmFuZ3VhcmQ=", "UmVkIExlZ2lvbg=="),
    ("VmF1bHQgRHdlbGxlcg==", "QnJvdGhlcmhvb2Qgb2YgU3RlZWw="), ("QWxveQ==", "U3lsZW5z"),
    ("U2VraXJv", "SXNzaGlu"), ("VGFtb24=", "SmluIFNha2Fp"),
    ("R29kcmlj", "UmFkYWhu"), ("TWFsZW5pYQ==", "TWFsaWtldGg="),
    ("UnVhbg==", "TGFudGVybg=="), ("R3VpbGQ=", "RmFjdGlvbg=="),

    # Mythology & Deities
    ("WmV1cw==", "UG9zZWlkb24="), ("SGFkZXM=", "UGVyc2VwaG9uZQ=="),
    ("VGhvcg==", "TG9raQ=="), ("T2Rpbg==", "RnJleWE="),
    ("QW51Ymlz", "T3Npcmlz"), ("UmE=", "SG9ydXM="),
    ("QXBvbGxv", "QXJ0ZW1pcw=="), ("QXJlcw==", "QXRoZW5h"),
    ("QWNoaWxsZXM=", "SGVjdG9y"), ("SGVyY3VsZXM=", "SHlkcmE="),
    ("RmVucmly", "Sm9ybXVuZ2FuZHI="), ("SGVybWVz", "RGlvbnlzdXM="),
    ("U2hpdmE=", "VmlzaG51"), ("QnJhaG1h", "SW5kcmE="),
    ("U3VuIFd1a29uZw==", "RXJsYW5nIFNoZW4="), ("VmFsaGFsbGE=", "SGVsaGVpbQ=="),
    ("TW91bnQgT2x5bXB1cw==", "VW5kZXJ3b3JsZA=="), ("RXhjYWxpYnVy", "TWpvbG5pcg=="),
    ("TWVkdXNh", "UGVyc2V1cw=="), ("TWlub3RhdXI=", "VGhlc2V1cw=="),
    ("U2lyZW4=", "SGFycHk="), ("VmFsa3lyaWU=", "RWluaGVyamFy"),
    ("VHJpZGVudA==", "VGh1bmRlcmJvbHQ="), ("U3BoaW54", "UGhvZW5peA=="),
    ("TmVjdGFy", "QW1icm9zaWE="), ("Q3JvbnVz", "VXJhbnVz"),
    ("UGFuZG9yYQ==", "UHJvbWV0aGV1cw=="), ("R2FpYQ==", "VXJhbnVz"),
    ("QXRsYXM=", "SHlwZXJpb24="), ("R3JpZmZpbg==", "Q2hpbWFlcmE="),

    # History & Pop Culture
    ("SnVsaXVzIENhZXNhcg==", "TWFyayBBbnRvbnk="), ("TmFwb2xlb24gQm9uYXBhcnRl", "RHVrZSBvZiBXZWxsaW5ndG9u"),
    ("QWxleGFuZGVyIHRoZSBHcmVhdA==", "RGFyaXVzIElJSQ=="), ("R2VuZ2hpcyBLaGFu", "S3VibGFpIEtoYW4="),
    ("Q2xlb3BhdHJh", "TmVmZXJ0aXRp"), ("S2luZyBBcnRodXI=", "TWVybGlu"),
    ("U2hlcmxvY2sgSG9sbWVz", "RHIuIFdhdHNvbg=="), ("QmF0bWFu", "VGhlIEpva2Vy"),
    ("U3VwZXJtYW4=", "TGV4IEx1dGhvcg=="), ("SXJvbiBNYW4=", "Q2FwdGFpbiBBbWVyaWNh"),
    ("SGFycnkgUG90dGVy", "TG9yZCBWb2xkZW1vcnQ="), ("R2FuZGFsZg==", "U2FydW1hbg=="),
    ("RnJvZG8gQmFnZ2lucw==", "U2Ftd2lzZSBHYW1nZWU="), ("THVrZSBTa3l3YWxrZXI=", "RGFydGggVmFkZXI="),
    ("SGFuIFNvbG8=", "Q2hld2JhY2Nh"), ("TmVv", "QWdlbnQgU21pdGg="),
    ("SW5kdXN0cmlhbCBSZXZvbHV0aW9u", "RGlnaXRhbCBBZ2U="), ("RmV1ZGFsIEphcGFu", "TWVkaWV2YWwgRXVyb3Bl"),
    ("Um9tYW4gRW1waXJl", "Qnl6YW50aW5lIEVtcGlyZQ=="), ("Q29sZCBXYXI=", "U3BhY2UgUmFjZQ=="),
    ("UmVuYWlzc2FuY2U=", "RW5saWdodGVubWVudA=="), ("R2xhZGlhdG9y", "Q2VudHVyaW9u"),
    ("U2FtdXJhaQ==", "TmluamE="), ("S25pZ2h0", "U3F1aXJl"),
    ("UGlyYXRl", "UHJpdmF0ZWVy"), ("VmlraW5n", "QmVyc2Vya2Vy"),
    ("U3BhcnRhbg==", "QXRoZW5pYW4="), ("T2x5bXBpY3M=", "Q29saXNldW0=")
]

def _decode(val: str) -> str:
    """Helper function to decode base64 strings."""
    return base64.b64decode(val.encode('utf-8')).decode('utf-8')

def get_random_word_pair():
    """Decodes a random pair at runtime without revealing plain text in code."""
    encoded_w1, encoded_w2 = random.choice(_ENCODED_DATA)
    w1, w2 = _decode(encoded_w1), _decode(encoded_w2)
    
    if random.choice([True, False]):
        return w1, w2
    return w2, w1
