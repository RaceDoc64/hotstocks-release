#!/usr/bin/env python3
"""Einrichtung des Hotstocks-Auto-Deploy-Agenten auf VPS3 (einmalig, danach keine Terminal-Eingaben mehr noetig).

  python3 install_hotstocks_autodeploy.py            -> Trockenlauf: prueft alles, schreibt NICHTS
  python3 install_hotstocks_autodeploy.py --apply    -> installiert Agent + systemd-Timer (alle 10 Minuten), erster Lauf als Trockenlauf
  python3 install_hotstocks_autodeploy.py --uninstall-> Timer/Dienst entfernen (Backups, Zustand und Websites bleiben)

Der Agent holt NUR freigegebene Release-Pakete aus https://github.com/RaceDoc64/hotstocks-release.git (Pull, keine offene Tuer), prueft Pfad, Dateityp,
SHA-256, Skripthosts, sichert jede Aenderung, tauscht atomar, prueft den Origin und rollt bei Fehlern selbst zurueck.
Er beruehrt nur die zwei statischen Site-Ordner, sein Backup- und Zustandsverzeichnis. Nicht: family-office-api, Postgres,
Redis, Caddy/Compose, DNS, Secrets, SSH. Pause jederzeit: touch /etc/hotstocks-autodeploy/PAUSE
"""
import argparse, base64, hashlib, json, os, pathlib, shutil, subprocess, sys, zlib
REPO = "https://github.com/RaceDoc64/hotstocks-release.git"
AGENT_SHA = "03a67532082c7d044c44b5a7342783db77ae678d8629af67d9a9acf42fe20670"
AGENT_B64 = "eNrNPGtz2ziS3/UrMNxLhUwkWnaS2TtlnD1NosTZcWKX7Z3dG42WRZGgxBFF6kjQj3j036+7AZLgQ7K9N3V1TkUSSaDRaPQbDf7pu4M8Sw/mYXzA42u2uRPLJH7VMwzjJBGZSLxVxsa5SAYf+CZK7gbjBY8FM+M8ZefUdnAp3Nh3U38ezqMwEUu+Yi/ZIhTw6eVpZNm93i8hXwoWpDxc8AWf85izCx5xN+MZc/OM8TDma/YpFCf5fHDBNwkzz/Mo6rMVPsHHC77ksc/ZzzwFVP08Xlgsj312zdOEBwHgFIUejJGFvOfmAfN5zDLhijDzoCM7S8NFGA+g9zcO7eIwy3hss79yADlGwClAHLGf3Sj0Q7pgg3fsR9db5Rv85Ypk7aY8BVIA1ByAwt2egnqe5jxQXeY8ZB/5MoKmbo6dJAYpu8i5t7rhC5v9BNNhv+SLNAwChriOzz/32QdX8Hjuxqs+e5/EwoV5p3D362WfXXIv5SIDOjLmIvntzR0bDJLY40z7Q7Af8tRbRgjUvE7WLLvLBF/7g6twTQgFC5gbEMuqQ/LTuwHMuYQENFqIPrtxswZQ4XLB+wxmBEs5FyxGmmd1YEh1WNLy7xekWOz3WcTFN1EtfJ+dAyH54NJbupHgaR1KmkTRHMjPPn8gKDCPKBKEjgvMcINrJoB7FDTiIh94SC3ZTQgrmzIgfI9GGRF9Q/aDl8RBuHD8MH13cD7+2+UEwEXAkzFLsEO4Zsh+g7/nwCjRdcUuxKIKiOznJet1KGDRbBSWXrjeJKlgbrrYuGkGRPKhrQC691ngAXf22dLNllE477PfsiTuswQosHGFvJUiVZe5CKEdEhA+8/kmTTyeQTNYxj6TsG7Xkc1Fyrk9ifgayHUFvxks1OSq1/t5cnH5+ewrO2bGoX1k9C4mX85+njgfT8efnC/jfzjjTxN4dvSavWCvvh8OGfsTm4Tx2o0GH1E03TlnQQ5UOE04LDFwNJAFaBC4RPvYBa6Hzsve+7OvHz9/AlAKf/scvs0ks0GDhGkS2wsuTOPkcvzBkU2NPjMOuPAOloVOGaB0+KRSDuSa2EgWw7J649PTs79PPjiTf1zBEPfGUqwjBOBlGX79Rp+38p64FfIedIXvGz7f0PVmIb84fW9i+squ6Sv0EtV27cZhwDMC4V6HgbHt/Xh69v4nGPzr+Mvkkob3XN+/C8KIYysfcOfpANZ+k2TcvpNY4LzpeylcD5cML2JQDbc2zo3A56Ar0/Ab950Vv8tgpPPx1YlzgQuSchsBwhBmavxzOh784g6+DQf/4fw6mNWu7IPZi38zrN7lybizJ7RyB8Hs/vvXW2z2YfJx/LfTK+fy/cXn8yvn5OzyCqc0NW5ubuxFkixAIt0FEAHkLkVARJby2QAeRHci9LLiWfbKFqnrgza+DvlN2SP0F6ieOh55fgzL6vMovE7tmAtj1uv1fB4Ar7vm3Br1ULRBt+VpXIiHDY+O3nwPT+0lv/XBYGTCtFS3OLkx670KKbPLH9imvMCPb0nM7Vx4BRCQr/WmAYYA25lIA+xhGs/+69n6mX/17OTZl2eXvxjY1YvcLGMf3TAyJ7ce34gwiRWQDTwpW5CBlPdxNMcJ41A4jpnxKOgzL1iAakjvjj+6UcZVf1Jw8Nj2YHmgRf0mtIbb8Fm/jWqCoyJryiEAmBrlU2Nm1fulaF6PmzAOmIEPjHrbOWnTnYNUj1ujRMnCQaHp7Fc8bPWS+Kh+bQzpQuqJjn4kre5mE4HuN0bsfgsMGMByqattvUuSC5SFWY9u/wlMTvGHNp504QE7TxORrMAUaY/Llc3cO7WoL1xtISM0FKCBQR38loSxCUxl3losSFJ2y9B8VXPepGEsTOwARiLKs+XxFbgSVgtRG2YFBo9aWr0SASCjQmCdLTQMwqBknOpmxezdC2WD2ULru14BsU15kRE+fcZvw0w4yaqB3k0olg0gCeBpGq5hoUkK6qMH9k0aCm4Gxr0SwS2rrAAsEcxi+2ts1Gbo+g4tLk20Y44Vx9iEZWZa9VFr/IGsYyPQzGz2TjkMJfgtKBsNgcy95vsReBSRSy5+CnnFelOXAsITie5keRCEt6ZhQxuj1kPSWE6EZuvn640+2z7wIDjH4vgQ/ArwWMgcyZErQGDKQRtErsdNgNlvImF1CA157V1Schd7DqqWJgEx2gC1FnpC8xz67NPnK+dqcvHl89fxqXN+cfbl/OrYGBrywfjyp/Px5eWxIQBfbeIQZvTZPC3I5U2lMpspzD3pkMxTN/aWaJfW4F4b1h+wRjhDCHXMF+D3gY/m3fjHX8HcNHiQECv9ORtcbXNqQDcDVQd0nMme8L+PZDmG/3DH3QAjcQfkf5MLhQaua/ETDBU8Oz48Glq10YAzU1tyoQfCVUeF0HFD8JjJkiEWoKpeVuoK8ZmOjmYW3hzRMzMF4oB3jF9pCHLLQJfRPdRN6p41Hb0aDmdWhyyUbXXhiROIIiuDBNrdRopYO8S4EDdsvKMJrST50Ha6Rhe5Al/HChfM8CJYJ+QFCH/AmBNbvBrKGyWjzCEEI95CJV5Bq8BxMOKjNvCUrxNB0DMuBgABfyYULRoKIi74PvwCcJeXnfiVcBC7h8CkHDCQYJYQo+Ovj5Or9yfOyWT8wdjZXy2cAnE9oJhGgsnAjyWInRAKdujQELXgukNRoN5Kk0Qom4bXun+kCTc+yowZSTU1azJW1pC/iuEDI4/nfOXGMRiES+jL7hHCd+nWaM2+5rhkoFMAOXRZNOsQAMo8UhjDr7qBQFTCLIwxAAZVCs+Jk0h+8JkKAey1C2uNj+mJYdsGOgpwbWfgzcASHBhS5uAO+AEZ2oDypnFwUDTfO+tveeSC9gGHOmXngeuze+hRnzeg7MZ35gZ1YSrUMLYhnZdNGyew8rFPM6H7eqcbCBkHK3CrY2i3By8ILyG091ZiN1ZzjO+PaYi0HLvPDq3p4HAG1vyGp2ZtDtQBkK3FcntwgBBjA9pNFPF9GwXQuoABwi1RsEsUcEhDLhmNjDqBGYaOEfYnZoiZFt3uQYkQEXcbmWFhPI3cfC5GHagVKpZHFV96S6CoA6GnAAtWMSflJHRXVU5LJ6y9l7DUHlxbisjr2CMghG77HI2OaeQiGPy70bJMxg8H2PudUdBDFAMRL/8gQgFxQevhXiMGDiXMYTuibCG7BncdWBHkBGNHdnL15ZSZBPZAjW210YJAOuNuilJo/LCGsHj6z3ezl3GCvtIt0EQgAe3PFcPrfoUbAZZO1bgZ2u1DWfViC8wggl/WQA0Fby0Fzw6gJaiqFFHMPNCygpDMUu94+qvxfGZO/4lfLy260pDuMJMpRppre5Em+cY8tFoN0Nymni7SJqy62IwOUPToZ6Z+H6AiaA+Bf8skkwxmg/eDGQqTOv5lZP1F9oX/MIylqZTpsM15+h8oFIzzQBsjcGNGFMqQQk3jcO1GOc8wyPhda1/6tZToIBysR8DoxAWIRDNUzIqoIXvo93Q2kWvm4GNMEHVlZ3bQcRfzXK4QInB8XNcTfM1OEIl7HKumxyIlxYCaKXNojSEnV3aQJmu04vHCJH2xo7eWcyvzaA1gWri1AxJqk98yY49YUbqPnO496lLR46+XdTrooSSseuxsyNBW/oVSi8DlMGKfJW3zXTe5Nmm+0n7LfnaYUVRk7sPwHEdmuGuCefTrJF26KO6c9NOA1P1IuiLbA5qNvmog9uj+JJIudGlYexwNatFnEXjJJa4SCFxEEKHThcXesaPhQzgPJtRR8x924plEPmCpiFLF0xzDEOCm45ZNiPkNTivye7q+I9tNGDbyBw4sF/yPHejEpwbqQwzxOEV7KNR4hRkVLgnlJXksyKC19D1SJHD2h0YR5+A9MxqmDgCVZ0xZThjADJwWeA8ZO+6AL2eMfQs9JGdVh0DiQTCGJBmpIwWkHBI6sHfH7LA9ABr9MM45+t5zwB/XrtowaYyS8QeMlORafblHRA92HzjT0ZvhDHwRdu9tK/sFy5HegNHgoH1iR+cO1ABq7sQRHT6ClP6a81K5LU2PxzRImg1aTiDrd8RJyvuKkwQ3AjQZRxgo4Y3kUqG6Ci8p9DUp9ouYowhRU7V3ZcAFNC0bruu5JdPHxgVotbFRzzBpzLIuzMOSrzFzBhM5REFV90Nf3oPxdsqq8UWNhbtpAOXg8wcWgBcC5NHEc5NJo49Q4WKvCoHnDQWC3ZX6gJ+oPHRlvXZvHYTZZ98Pd+tBYxx/c5cROwN/28UEOo91zaKnshLhRoDusEqWggKXGVtdWSRkeTcNVbEKccOxXP1KdwJXWP3iAp/jpUz/FLGceojBn9FQHBgAlim5KlytRaCEPKlA9HywwwE55w0NgRiS9dvkwmhLYYDuNDIRGhZiNxylA5Suz3YZot0RBgv4MhJy15M4e6dub0hxILl5fifQPdqFkdynUuFtQXTa3pGOF/EWbgWRgJMET4sGs0fMgTbes3y95orbH0QfEEMGluO1ORipJyeFjOwMh0P8/3hyfssZuNRZ9iAekr1fHlfYtH30RylDbWLK8BbJsdKnKlgfQm1KDpcRCrVA8usmWy3pv7AakgQ0fMhTUZofsxxZspv1IHVQ1Is9D5MkpFOVdxjNSqzINrSxFs10fWVVygyT7ip2OYmt/pz2A4kOuO/BR7vCBX05aAPRjYyHfP7Op0pl3QHZMf3NgdbZJpU79mYBukFovBKpya3p6PBoOOsivO5B7OdZINf01Wz/0kGbfUuESdJr3rFGtexwLRhQXUoGRvUh7TPed4LIXTjXmGY0rYeFViEAVk+AP+CuRHhNfGu2aiKQa4sKEsrfOKqy4uzr+wlqT1XjkiWpH/PUMnZqxHo4QaG/FlOAKjMPq51CtLjQ77YyXTrdUH8dDh8hl2qaGHtQdUc1KlVQgd4LYboAi/3GH20HiOx5xn1Hoz0IEEZquya/P1zag3tBe7UQD6Dm5WkjDNljpgppjHxHqTprp/SiqgTghWrU+sweGbcX09EMF9YOqEKqB2dG8qMwXgPLkWGgrSxS5SiXhN8P7I20XHsVEYiUeVv44hYyHFKu4r5pfYyZ9cRJFoEAZ194ugIWk5LE40fMM+NPYI5qIWQRl442YAEzgrtYHvhEw1NqG80KzDFn1TY9D0ZS2q5D6fyye9SFrRS81LNt50QFH6V/cvRmh4Oi67iiPq7wTNqZ43Wfpt2xYaPXKPplEWXX3g1tVtXyKnkaoQe9fwNnit+zZqJfnzc0Ew7edwAgTvp+a3Vv+2CjOhm8tU/VTp7afxtQWdaACpOO5E4fFYIN6OMGP3+Nn91jitJBmdjiFptM+dOeFm24vCxmNtuzB9geeSX3zsAiJhGxFBZBTJ9jfu75bDt6/foV2OQ/20P4d/h0LIMyIasBvVeIbo0K1Y6NaMC1c69Z239J/Ls+c6AVDIdBTbHzm25AvkPkZHNu/Bq3WQtzMdQJdMoQAi2EJPnsP6k211tzsUz8ko0UxmZ9I00BA/ID9eHRdMQGqOpq5nMms/g7ratMCxQguop+YkqRdLI3FhXdFfLXmSlQQlRwbz21gE2rnNe8CsJBCztzDvqJN2LxOenzdm0bpmbDLIEeEFOZ8bzKZv+CjPESNP5wiHHVO71UrsNpnN4DUtsZtMKsJOVMqcozXDCzwordx/Nt05splkMqd0NbJgrYp5tqt5BIAvPZTIczNJoyLTPr7UHoXpLmOW3YPO+z588tdFylywku7bYq18ZkEz3AYSw2YFqjIvYoE63aJBC9VVdAUaC8k2pwdb8afb+tmRFm3pdB3Jb9aNWXcl+NEDNEivWkMdZWG+3MsxvtKmWalnVusynQbUalbyIzRkVxI9afYgXCCL6pRhsNgMhjY9uJh2xj1EhECQegyP1mejjTd4BdCCXqiVksQT4uai/8MFs5eeYuuFlWTTSSJZZlU5+DA3b04sXRsJkcoYc/1A1gGDt421mHc2D1V51Rec3iwoRBooGh8dgB7i5HrvgGi4VQtuxLWFupuSxxbBY9HqCeRsYclCVrRq1PZ63QGlTe8TD581ArzAFPO6HsFaodPaykeJn7shfYzRB+LnSFsZdd20yyK0HVkTvCRavyBQ3G8IinKEU2UoNj+hMuCAdD4Q3XfNtcvw5niDYCBXFvhyOOOnGuijwfk/Ga/wvVio0SIS/Z3B2ZEM/Pu3c/sUC5nRGhbEn99sNxpjqTINXsPBSLCA8VdLifQHU736C2N4mHkFr2pfP5y9mHCQgTUM/B+xaxybG8UTCMulzgpXKIjzsmUR8UubKK1r3qoVmsBrVQCezu0sL7IiuOrIGjGx6MKFmj0kYIB27gFzISsCVqK9Cm7LoorCk4/bprJxa+1rgRu63qF7W51Na0VrbjyJyeg96HmlJxykRPjcOw4BTNIxhEBbF9PdOMMxe8kX5upZKeKKlPlNYicbw/d0JA7TyOwni1Ywsd8UYtpPa3tDNRbB0KBsQJeBqjdfVdvOEXpTmZm4NdZa+HrxnYnoByJXHImR/KUip1asbaGSZicKMkl4SpY+K7Y0w5MyX36RrlvnsklY07u5ykaZLuBkhV+10P1GqXgaC2oFTc+cS8Gc16d8liSzu+bZgCZJGdikBTAqUCeEI8TVtCBVW7ibHEanx0SDbZA7MoAULLPRA3NFtoU0y3mKi0gfSsmtVG02vD5PvXrzthouj5Usywooz75vS2SmVMixn22YuShZTRmBX+1m05u32ZDl+ZnMLGv3kDE0gy21smN+AEdhnwej23kBXcsbvmYEnwCwtt7WXm+o1q7nZVt1Ti5GmqQQENWaFN7KBhQjdLXN62KrpFe5w9bF/u0VjW/1bjPU6FeSQBTqEdVX6BhpGZRy1S7BbHRZKg5FD4ifUqoLX67PXh8CnZJokFRq1/ECIw76PhsNx3QciU0y3p29uZ6Dcx+jj7CT5ox5ugyqAWbn0cfz5llJ0IDJWlkSHKfQvJLZ5SvZeZg51paoS+Q2EoK1lwCeYxnjoQcg0ZeRUGg8SGwZ2BFtfqqmjoXoRr6RxgzQf8xExLx3ZEg/jXag+SjqhiCg1cdFqNdi6UBiw1yHVRUUJJxUzi+kesVnl2+P56+hzng5kb+AnzgV9/9FpJSj9xrKcFgw9ILybRHk02XWY6qXdJ9Ym8LON+kGAE8TuC+FiaPW4M5XSUJwPlPiC6WXHy325v/xDjPIvd5Rp3XXgjGVw0fjCT83Fycjq5AAhFD8Kz+wx6gzZqCy0TScrJ8e94jGfNVCxMQ32aXL4/OR1/mnzts295ioAXHA9tCx2Ft8V57HsE21wTPUZ6W5w/Kfpa7QOFJQJVQZM8oEJnb6k3qiPMy2wNybZglZARgVWVdZN8U+B1UFCkjeDTki0yZ0C3UknCfhHJjtj0Qaxm2305scnFx7PTTxeTz+9PtKnb5XKOOg/OU+d2TtaoIBhVLVSx+jK3SROoOC5vVDfVAixq24wUO0udAjrB4OG086kMCGft3EUNeD5VoSJQnnuFwp/J8IhOeUVaOrGs5YYnRXqiY2du3hylnEKZetAG2z2UvrNZOJWlg4ySryIp0Qiy5LsJlnTwIYp4/P/coaXZgyeJhpZ+L/D3H+fearE7bQvP+wiq5eDS0IgkjN30c3eg+KDXS/up+2Kzjki6lE+0RQ3NZyjR6dheePA9C41th46tdap50EW2fNg8WqlEvX2AulW8YCCa9eoFqofIYzqQkyaCe+KS3iJyjLtgHpb1qNd/zN2Umfg+ltTNvSVEIHyBm6xWJ4qqLKOBaFAVWFaTsXZnWNTEtEo38t7M8qy/ifsAgYosKUzGu7gj3vEujN5jMgZqyAbxwRHM8jV39izCU+eGee968ZbZXWSh6jGfUPgSlGz8tjKmRpMl25Ut18Xiwqp/u7GZO19w3KuobafsI558MUJLGE7cfCPohTIdm224KdkgZZSAPTum5EvrpF/n/sq/fqBXG47OsrdlCJ/SuYe6o4a3G9asq9SM3gVjB9jaxA/1dhgbj6o5k3+w3/Xrrz829NUDma1KN+GeF76u6BSJTKVNBqy94uWhjrcp39BSpOVggvR6m50Hcasx5GtwYBYrN7LkICB8arsJwiU37hyz2iCV5+qrKS7BayjzoeWx8RqV6yeGn4gpHlF/AqKptifUKgCvkPKpsCFJwdswN9LiVfERch+e2aJsJfnzqLroii6pQSn0FOPoGeZEbhqFBDFEiDgc9AtrB4yabippj84m6n0Ys849WDrCf4+rAI57+X4u2t2EYa1tnyX4pi15B3Gzav6lVyvXJm8vJBcGmz5CNLQKzPqGe9qVTSNHL6NMktqJ7vZx5uCLrlD/XPBwyeMgiRb0QjF66VTce1oZZ4dzPv7x0+R0cvL16qCMwPZF6936qivoKJZqZ8zBUQmokAOLOl8Ph7PtbrC1AAoVOV/GQqsJxdP7XYjTuh52Eeoxwe4Oqv3t6+Ti7+OLq8kV0uu79P+WYiDN+0jWmLFCv3wRiPUEG9TlJ7TP7nrqzUT4WopCi7noTRdvE7PH6SLHt32d41Wx8eFubNf3HVc9Mw35TjgwTq6Hy3JsUFDnyJdlvO1qr978tqPLrlHK/Nmjxymi0gImzm1j09ywXbH97AWLeqypjFMrniSHmN60ZJZvVHJxDRyYjWyCh9ltiWm1MO6i2/TIN/EEhny74b16kRqoQWk6yMYBp7aM5XN6/rwyQTojS6BawI0BAupOwKKpspE9f9fkstWyYO5GQL0iDS+tTxfY6eDNaDYqUJHJNYANfkdH6+lqpsruMuNR45RINYfBJF1zmFI8i1GkONJJEFmS3pKMYbWSBQc9vJYhKHnkr/b8aNgKVPv8E/bEY+gqnVNYULzfcGzlRIvqSrm1Xy20rENNljFXiSbNwTjSJ1DkXXCE4n1aFLl2Yb9JNjr2b7toWz3fqwHxcFrOo6gRwWrlQURdshgVyC3b0U3hounIhj9VM/jqCU4ffH25CrttryK1sq7ALrwCfgiKM8R3rKHb5TjkDTgOqlHHUf5AdkfblsKUytXq/Q906lYe"
SITES = {"pharma": {"root": "/opt/joe-platform/apps/pharma-site", "host": "www.pharma-hotstocks.net"},
         "rohstoff": {"root": "/opt/joe-platform/apps/rohstoff-site", "host": "www.rohstoff-hotstocks.net"}}
BIN = pathlib.Path("/opt/hotstocks-autodeploy"); CFG = pathlib.Path("/etc/hotstocks-autodeploy")
STATE = pathlib.Path("/var/lib/hotstocks-autodeploy"); BACKUP = pathlib.Path("/opt/joe-platform/backups/autodeploy")
LOG = pathlib.Path("/opt/joe-platform/logs/infra_change_log.txt")
UNIT = "/etc/systemd/system/hotstocks-autodeploy"
SERVICE = f"""[Unit]
Description=Hotstocks Auto-Deploy (Pull freigegebener Releases)
After=network-online.target docker.service
Wants=network-online.target
[Service]
Type=oneshot
Environment=HOME={STATE}
ExecStart=/usr/bin/python3 {BIN}/agent.py --once
TimeoutStartSec=600
Nice=10
NoNewPrivileges=true
PrivateTmp=true
ProtectHome=true
ProtectSystem=strict
ReadWritePaths={SITES['pharma']['root']} {SITES['rohstoff']['root']} {BACKUP} {STATE} {LOG.parent}
CapabilityBoundingSet=CAP_CHOWN CAP_DAC_OVERRIDE CAP_FOWNER
"""
TIMER = """[Unit]
Description=Hotstocks Auto-Deploy alle 10 Minuten
[Timer]
OnBootSec=3min
OnCalendar=*:0/10
Persistent=true
RandomizedDelaySec=20
[Install]
WantedBy=timers.target
"""
def run(*c, **k):
    return subprocess.run(c, capture_output=True, text=True, **k)
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--apply", action="store_true"); ap.add_argument("--uninstall", action="store_true")
    ap.add_argument("--allow-remove-once", action="store_true", help="legt eine auf 24 h befristete, einmal nutzbare Freigabe fuer Seiten-Loeschungen an")
    a = ap.parse_args(); ok = True
    def chk(good, msg):
        nonlocal ok; ok &= bool(good); print(("OK   " if good else "FEHL ") + msg)
    chk(os.geteuid() == 0, "als root ausgefuehrt")
    if a.uninstall:
        if os.geteuid() != 0: return 1
        run("systemctl", "disable", "--now", "hotstocks-autodeploy.timer")
        for p in (UNIT + ".service", UNIT + ".timer"): pathlib.Path(p).unlink(missing_ok=True)
        run("systemctl", "daemon-reload"); print("Agent-Timer entfernt. Backups/Zustand/Websites unveraendert."); return 0
    data = zlib.decompress(base64.b64decode(AGENT_B64)); chk(hashlib.sha256(data).hexdigest() == AGENT_SHA, "Agent-Paket intakt " + AGENT_SHA[:12])
    for tool in ("git", "curl", "python3", "systemctl"): chk(shutil.which(tool), f"{tool} vorhanden")
    chk(sys.version_info >= (3, 8), "Python >= 3.8")
    for name, s in SITES.items():
        chk(pathlib.Path(s["root"], "index.html").is_file(), f"{name}: {s['root']}/index.html vorhanden")
        r = run("curl", "-sk", "--resolve", f"{s['host']}:443:127.0.0.1", "-m", "20", "-o", "/dev/null", "-w", "%{http_code}", f"https://{s['host']}/")
        chk(r.stdout.strip() == "200", f"{name}: Origin liefert HTTPS 200 (lokal)")
    r = run("git", "ls-remote", REPO, "HEAD"); chk(r.returncode == 0, "Release-Repo erreichbar (lesend)")
    free = shutil.disk_usage("/opt").free // 2**20; chk(free > 1000, f"freier Platz {free} MiB")
    if not ok: print("ABBRUCH: Voraussetzungen nicht erfuellt, nichts geschrieben."); return 2
    if not a.apply: print("TROCKENLAUF beendet - nichts geschrieben. Mit --apply installieren."); return 0
    for d in (BIN, CFG, STATE, BACKUP): d.mkdir(parents=True, exist_ok=True)
    os.chmod(STATE, 0o700); os.chmod(BACKUP, 0o700)
    (BIN / "agent.py").write_bytes(data); os.chmod(BIN / "agent.py", 0o755)
    cfg = {"repo": REPO, "branch": "main", "sites": SITES, "state_dir": str(STATE), "backup_dir": str(BACKUP), "log_file": str(LOG),
           "max_ops": 60, "max_file_bytes": 6000000, "allow_remove": False}
    (CFG / "config.json").write_text(json.dumps(cfg, indent=1)); os.chmod(CFG / "config.json", 0o644)
    pathlib.Path(UNIT + ".service").write_text(SERVICE); pathlib.Path(UNIT + ".timer").write_text(TIMER)
    r = run("systemd-analyze", "verify", UNIT + ".service"); print("systemd-Pruefung:", (r.stderr.strip() or "ok")[:300])
    print("Erster Lauf (Trockenlauf):"); r = run(sys.executable, str(BIN / "agent.py"), "--dry-run"); print(r.stdout[-1500:], r.stderr[-500:])
    if r.returncode not in (0, 1): print("Trockenlauf fehlgeschlagen - Timer NICHT aktiviert"); return 3
    run("systemctl", "daemon-reload"); e = run("systemctl", "enable", "--now", "hotstocks-autodeploy.timer"); print(e.stdout, e.stderr)
    t = run("systemctl", "list-timers", "hotstocks-autodeploy.timer", "--no-pager"); print(t.stdout)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f: f.write(f"autodeploy-agent installiert (sha {AGENT_SHA[:12]}), Repo {REPO}, Timer alle 10 min; Pause: {CFG}/PAUSE; Entfernen: install --uninstall\n")
    if a.allow_remove_once:
        (STATE / "ALLOW_REMOVE_ONCE").write_text("einmalig, verfaellt nach 24 h oder nach der ersten Loeschung\n"); print("Einmal-Freigabe fuer Loeschungen angelegt (24 h, einmalig).")
    print("ERGEBNIS: INSTALLIERT. Status: python3", BIN / "agent.py", "--status | Pause: touch", CFG / "PAUSE"); return 0
if __name__ == "__main__":
    sys.exit(main())
