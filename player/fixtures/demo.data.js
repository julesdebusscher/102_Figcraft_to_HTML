// Reference instance of the data.js contract (see the plan).
window.FIGCRAFT_PROTOTYPE = {
 "version": 1,
 "title": "Démo FigCraft",
 "start": "1",
 "panel": [
  {
   "section": "Parcours principal",
   "screens": [
    "1",
    "2"
   ]
  },
  {
   "section": "Annexes",
   "screens": [
    "3"
   ]
  }
 ],
 "pageName": "Page 1",
 "screens": {
  "1": {
   "name": "Home",
   "width": 390,
   "height": 844,
   "background": "#f4f6fb",
   "root": "1",
   "overflow": "none"
  },
  "2": {
   "name": "Détails",
   "width": 390,
   "height": 844,
   "background": "#eef7ee",
   "root": "2",
   "overflow": "none"
  },
  "3": {
   "name": "Écran / 🚀 \"test\"",
   "width": 390,
   "height": 844,
   "background": "#fff4e5",
   "root": "3",
   "overflow": "vertical"
  },
  "4": {
   "name": "Menu overlay",
   "width": 260,
   "height": 300,
   "background": "#ffffff",
   "root": "4",
   "overflow": "none"
  },
  "5": {
   "name": "Second menu",
   "width": 300,
   "height": 180,
   "background": "#fffde7",
   "root": "5",
   "overflow": "none"
  }
 },
 "nodes": {
  "1": {
   "id": "1",
   "name": "Home",
   "kind": "frame",
   "x": 0,
   "y": 0,
   "w": 390,
   "h": 844,
   "rotation": 0,
   "opacity": 1,
   "visible": true,
   "clip": true,
   "overflow": "none",
   "position": "scroll",
   "paint": {
    "src": "assets/home_bg.svg",
    "dx": 0,
    "dy": 0,
    "w": 390,
    "h": 844
   },
   "alts": [],
   "css": {},
   "liveText": null,
   "bindings": {},
   "instance": null,
   "children": [
    "1.hdr",
    "1.card",
    "1.btn",
    "1.count",
    "1.cbtn",
    "1.theme",
    "1.surf",
    "1.menu",
    "1.badge"
   ],
   "interactions": [
    {
     "trigger": {
      "type": "afterDelay",
      "delayMs": 2000
     },
     "actions": [
      {
       "type": "setVariable",
       "variable": "v.badge",
       "value": true
      }
     ]
    },
    {
     "trigger": {
      "type": "key",
      "key": "Shift+K"
     },
     "actions": [
      {
       "type": "setVariable",
       "variable": "v.count",
       "expr": {
        "op": {
         "op": "add",
         "args": [
          {
           "value": {
            "type": "alias",
            "value": "v.count"
           }
          },
          {
           "value": {
            "type": "number",
            "value": 10
           }
          }
         ]
        }
       }
      }
     ]
    },
    {
     "trigger": {
      "type": "key",
      "key": "Gamepad A"
     },
     "actions": [
      {
       "type": "setVariable",
       "variable": "v.count",
       "expr": {
        "op": {
         "op": "add",
         "args": [
          {
           "value": {
            "type": "alias",
            "value": "v.count"
           }
          },
          {
           "value": {
            "type": "number",
            "value": 10
           }
          }
         ]
        }
       }
      }
     ]
    }
   ]
  },
  "1.hdr": {
   "id": "1.hdr",
   "name": "Header",
   "kind": "leaf",
   "x": 0,
   "y": 0,
   "w": 390,
   "h": 64,
   "rotation": 0,
   "opacity": 1,
   "visible": true,
   "clip": false,
   "overflow": "none",
   "position": "fixed",
   "paint": {
    "src": "assets/header.svg",
    "dx": 0,
    "dy": 0,
    "w": 390,
    "h": 64
   },
   "alts": [],
   "css": {},
   "liveText": null,
   "bindings": {},
   "instance": null,
   "children": [],
   "interactions": []
  },
  "1.card": {
   "id": "1.card",
   "name": "Card",
   "kind": "leaf",
   "x": 45,
   "y": 100,
   "w": 300,
   "h": 120,
   "rotation": 0,
   "opacity": 1,
   "visible": true,
   "clip": false,
   "overflow": "none",
   "position": "scroll",
   "paint": {
    "src": "assets/card_a.svg",
    "dx": 0,
    "dy": 0,
    "w": 300,
    "h": 120
   },
   "alts": [],
   "css": {},
   "liveText": null,
   "bindings": {},
   "instance": null,
   "children": [],
   "interactions": []
  },
  "1.btn": {
   "id": "1.btn",
   "name": "Button",
   "kind": "instance",
   "x": 115,
   "y": 260,
   "w": 160,
   "h": 48,
   "rotation": 0,
   "opacity": 1,
   "visible": true,
   "clip": false,
   "overflow": "none",
   "position": "scroll",
   "paint": null,
   "alts": [],
   "css": {},
   "liveText": null,
   "bindings": {},
   "instance": {
    "set": "Button",
    "variant": "Default",
    "variants": {
     "Default": [
      "1.btn~Default~bg"
     ],
     "Hover": [
      "1.btn~Hover~bg"
     ],
     "Pressed": [
      "1.btn~Pressed~bg"
     ]
    }
   },
   "children": [
    "1.btn~Default~bg"
   ],
   "interactions": [
    {
     "trigger": {
      "type": "hover"
     },
     "actions": [
      {
       "type": "changeTo",
       "variant": "Hover",
       "transition": {
        "type": "dissolve",
        "durationMs": 150,
        "easing": {
         "type": "easeOut"
        }
       }
      }
     ]
    },
    {
     "trigger": {
      "type": "mouseLeave"
     },
     "actions": [
      {
       "type": "changeTo",
       "variant": "Default",
       "transition": {
        "type": "dissolve",
        "durationMs": 150,
        "easing": {
         "type": "easeOut"
        }
       }
      }
     ]
    },
    {
     "trigger": {
      "type": "press"
     },
     "actions": [
      {
       "type": "changeTo",
       "variant": "Pressed",
       "transition": {
        "type": "instant",
        "durationMs": 300,
        "easing": {
         "type": "easeOut"
        }
       }
      }
     ]
    },
    {
     "trigger": {
      "type": "click"
     },
     "actions": [
      {
       "type": "navigate",
       "dest": "2",
       "transition": {
        "type": "push",
        "durationMs": 400,
        "easing": {
         "type": "easeOut"
        },
        "direction": "left"
       }
      }
     ]
    }
   ]
  },
  "1.btn~Default~bg": {
   "id": "1.btn~Default~bg",
   "name": "Bg",
   "kind": "leaf",
   "x": 0,
   "y": 0,
   "w": 160,
   "h": 48,
   "rotation": 0,
   "opacity": 1,
   "visible": true,
   "clip": false,
   "overflow": "none",
   "position": "scroll",
   "paint": {
    "src": "assets/btn_default.svg",
    "dx": 0,
    "dy": 0,
    "w": 160,
    "h": 48
   },
   "alts": [],
   "css": {},
   "liveText": null,
   "bindings": {},
   "instance": null,
   "children": [],
   "interactions": []
  },
  "1.btn~Hover~bg": {
   "id": "1.btn~Hover~bg",
   "name": "Bg",
   "kind": "leaf",
   "x": 0,
   "y": 0,
   "w": 160,
   "h": 48,
   "rotation": 0,
   "opacity": 1,
   "visible": true,
   "clip": false,
   "overflow": "none",
   "position": "scroll",
   "paint": {
    "src": "assets/btn_hover.svg",
    "dx": 0,
    "dy": 0,
    "w": 160,
    "h": 48
   },
   "alts": [],
   "css": {},
   "liveText": null,
   "bindings": {},
   "instance": null,
   "children": [],
   "interactions": []
  },
  "1.btn~Pressed~bg": {
   "id": "1.btn~Pressed~bg",
   "name": "Bg",
   "kind": "leaf",
   "x": 0,
   "y": 0,
   "w": 160,
   "h": 48,
   "rotation": 0,
   "opacity": 1,
   "visible": true,
   "clip": false,
   "overflow": "none",
   "position": "scroll",
   "paint": {
    "src": "assets/btn_pressed.svg",
    "dx": 0,
    "dy": 0,
    "w": 160,
    "h": 48
   },
   "alts": [],
   "css": {},
   "liveText": null,
   "bindings": {},
   "instance": null,
   "children": [],
   "interactions": []
  },
  "1.count": {
   "id": "1.count",
   "name": "Compteur",
   "kind": "text",
   "x": 45,
   "y": 330,
   "w": 300,
   "h": 32,
   "rotation": 0,
   "opacity": 1,
   "visible": true,
   "clip": false,
   "overflow": "none",
   "position": "scroll",
   "paint": null,
   "alts": [],
   "css": {},
   "liveText": {
    "var": "v.count",
    "style": {
     "fontFamily": "Inter, sans-serif",
     "fontSize": 24,
     "fontWeight": 600,
     "lineHeight": 32,
     "letterSpacing": 0,
     "color": "#1a1a2e",
     "align": "center"
    }
   },
   "bindings": {},
   "instance": null,
   "children": [],
   "interactions": []
  },
  "1.cbtn": {
   "id": "1.cbtn",
   "name": "+1",
   "kind": "leaf",
   "x": 115,
   "y": 380,
   "w": 160,
   "h": 48,
   "rotation": 0,
   "opacity": 1,
   "visible": true,
   "clip": false,
   "overflow": "none",
   "position": "scroll",
   "paint": {
    "src": "assets/btn_count.svg",
    "dx": 0,
    "dy": 0,
    "w": 160,
    "h": 48
   },
   "alts": [],
   "css": {},
   "liveText": null,
   "bindings": {},
   "instance": null,
   "children": [],
   "interactions": [
    {
     "trigger": {
      "type": "click"
     },
     "actions": [
      {
       "type": "setVariable",
       "variable": "v.count",
       "expr": {
        "op": {
         "op": "add",
         "args": [
          {
           "value": {
            "type": "alias",
            "value": "v.count"
           }
          },
          {
           "value": {
            "type": "number",
            "value": 1
           }
          }
         ]
        }
       }
      }
     ]
    }
   ]
  },
  "1.theme": {
   "id": "1.theme",
   "name": "Thème",
   "kind": "leaf",
   "x": 115,
   "y": 450,
   "w": 160,
   "h": 48,
   "rotation": 0,
   "opacity": 1,
   "visible": true,
   "clip": false,
   "overflow": "none",
   "position": "scroll",
   "paint": {
    "src": "assets/btn_theme.svg",
    "dx": 0,
    "dy": 0,
    "w": 160,
    "h": 48
   },
   "alts": [],
   "css": {},
   "liveText": null,
   "bindings": {},
   "instance": null,
   "children": [],
   "interactions": [
    {
     "trigger": {
      "type": "click"
     },
     "actions": [
      {
       "type": "conditional",
       "blocks": [
        {
         "condition": {
          "op": {
           "op": "equals",
           "args": [
            {
             "value": {
              "type": "alias",
              "value": "v.mode"
             }
            },
            {
             "value": {
              "type": "string",
              "value": "Light"
             }
            }
           ]
          }
         },
         "actions": [
          {
           "type": "setVariableMode",
           "collection": "c.theme",
           "mode": "m.dark"
          },
          {
           "type": "setVariable",
           "variable": "v.mode",
           "value": "Dark"
          }
         ]
        },
        {
         "actions": [
          {
           "type": "setVariableMode",
           "collection": "c.theme",
           "mode": "m.light"
          },
          {
           "type": "setVariable",
           "variable": "v.mode",
           "value": "Light"
          }
         ]
        }
       ]
      }
     ]
    }
   ]
  },
  "1.surf": {
   "id": "1.surf",
   "name": "Surface",
   "kind": "leaf",
   "x": 25,
   "y": 520,
   "w": 340,
   "h": 90,
   "rotation": 0,
   "opacity": 1,
   "visible": true,
   "clip": false,
   "overflow": "none",
   "position": "scroll",
   "paint": {
    "src": "assets/surface_light.svg",
    "dx": 0,
    "dy": 0,
    "w": 340,
    "h": 90
   },
   "alts": [
    {
     "when": {
      "modes": {
       "c.theme": "m.dark"
      }
     },
     "paint": {
      "src": "assets/surface_dark.svg",
      "dx": 0,
      "dy": 0,
      "w": 340,
      "h": 90
     }
    }
   ],
   "css": {},
   "liveText": null,
   "bindings": {},
   "instance": null,
   "children": [],
   "interactions": []
  },
  "1.menu": {
   "id": "1.menu",
   "name": "Menu",
   "kind": "leaf",
   "x": 135,
   "y": 650,
   "w": 120,
   "h": 40,
   "rotation": 0,
   "opacity": 1,
   "visible": true,
   "clip": false,
   "overflow": "none",
   "position": "scroll",
   "paint": {
    "src": "assets/btn_menu.svg",
    "dx": 0,
    "dy": 0,
    "w": 120,
    "h": 40
   },
   "alts": [],
   "css": {},
   "liveText": null,
   "bindings": {},
   "instance": null,
   "children": [],
   "interactions": [
    {
     "trigger": {
      "type": "click"
     },
     "actions": [
      {
       "type": "openOverlay",
       "dest": "4",
       "position": "center",
       "closeOnClickOutside": true,
       "background": "rgba(0,0,0,0.4)",
       "transition": {
        "type": "dissolve",
        "durationMs": 200,
        "easing": {
         "type": "easeOut"
        }
       }
      }
     ]
    }
   ]
  },
  "2": {
   "id": "2",
   "name": "Détails",
   "kind": "frame",
   "x": 0,
   "y": 0,
   "w": 390,
   "h": 844,
   "rotation": 0,
   "opacity": 1,
   "visible": true,
   "clip": true,
   "overflow": "none",
   "position": "scroll",
   "paint": {
    "src": "assets/detail_bg.svg",
    "dx": 0,
    "dy": 0,
    "w": 390,
    "h": 844
   },
   "alts": [],
   "css": {},
   "liveText": null,
   "bindings": {},
   "instance": null,
   "children": [
    "2.hdr",
    "2.card",
    "2.blur",
    "2.fuzzy",
    "2.drag",
    "2.back",
    "2.next"
   ],
   "interactions": []
  },
  "2.hdr": {
   "id": "2.hdr",
   "name": "Header",
   "kind": "leaf",
   "x": 0,
   "y": 0,
   "w": 390,
   "h": 64,
   "rotation": 0,
   "opacity": 1,
   "visible": true,
   "clip": false,
   "overflow": "none",
   "position": "fixed",
   "paint": {
    "src": "assets/header.svg",
    "dx": 0,
    "dy": 0,
    "w": 390,
    "h": 64
   },
   "alts": [],
   "css": {},
   "liveText": null,
   "bindings": {},
   "instance": null,
   "children": [],
   "interactions": []
  },
  "2.card": {
   "id": "2.card",
   "name": "Card",
   "kind": "leaf",
   "x": 25,
   "y": 120,
   "w": 340,
   "h": 200,
   "rotation": 0,
   "opacity": 1,
   "visible": true,
   "clip": false,
   "overflow": "none",
   "position": "scroll",
   "paint": {
    "src": "assets/card_b.svg",
    "dx": 0,
    "dy": 0,
    "w": 340,
    "h": 200
   },
   "alts": [],
   "css": {},
   "liveText": null,
   "bindings": {},
   "instance": null,
   "children": [],
   "interactions": [
    {
     "trigger": {
      "type": "click"
     },
     "actions": [
      {
       "type": "navigate",
       "dest": "3",
       "transition": {
        "type": "smartAnimate",
        "durationMs": 500,
        "easing": {
         "type": "gentle"
        }
       }
      }
     ]
    }
   ]
  },
  "2.blur": {
   "id": "2.blur",
   "name": "Verre",
   "kind": "leaf",
   "x": 25,
   "y": 300,
   "w": 340,
   "h": 120,
   "rotation": 0,
   "opacity": 1,
   "visible": true,
   "clip": false,
   "overflow": "none",
   "position": "scroll",
   "paint": {
    "src": "assets/blur_panel.svg",
    "dx": 0,
    "dy": 0,
    "w": 340,
    "h": 120
   },
   "alts": [],
   "css": {
    "backdropBlur": 12,
    "radius": [
     16,
     16,
     16,
     16
    ]
   },
   "liveText": null,
   "bindings": {},
   "instance": null,
   "children": [],
   "interactions": []
  },
  "2.back": {
   "id": "2.back",
   "name": "Retour",
   "kind": "leaf",
   "x": 25,
   "y": 700,
   "w": 120,
   "h": 40,
   "rotation": 0,
   "opacity": 1,
   "visible": true,
   "clip": false,
   "overflow": "none",
   "position": "scroll",
   "paint": {
    "src": "assets/btn_back.svg",
    "dx": 0,
    "dy": 0,
    "w": 120,
    "h": 40
   },
   "alts": [],
   "css": {},
   "liveText": null,
   "bindings": {},
   "instance": null,
   "children": [],
   "interactions": [
    {
     "trigger": {
      "type": "click"
     },
     "actions": [
      {
       "type": "back"
      }
     ]
    }
   ]
  },
  "2.next": {
   "id": "2.next",
   "name": "Suite",
   "kind": "leaf",
   "x": 205,
   "y": 696,
   "w": 160,
   "h": 48,
   "rotation": 0,
   "opacity": 1,
   "visible": true,
   "clip": false,
   "overflow": "none",
   "position": "scroll",
   "paint": {
    "src": "assets/btn_next.svg",
    "dx": 0,
    "dy": 0,
    "w": 160,
    "h": 48
   },
   "alts": [],
   "css": {},
   "liveText": null,
   "bindings": {},
   "instance": null,
   "children": [],
   "interactions": [
    {
     "trigger": {
      "type": "click"
     },
     "actions": [
      {
       "type": "navigate",
       "dest": "3",
       "transition": {
        "type": "moveIn",
        "durationMs": 350,
        "easing": {
         "type": "easeOutBack"
        },
        "direction": "bottom"
       }
      }
     ]
    }
   ]
  },
  "3": {
   "id": "3",
   "name": "Écran / 🚀 \"test\"",
   "kind": "frame",
   "x": 0,
   "y": 0,
   "w": 390,
   "h": 844,
   "rotation": 0,
   "opacity": 1,
   "visible": true,
   "clip": true,
   "overflow": "vertical",
   "position": "scroll",
   "paint": {
    "src": "assets/test_bg.svg",
    "dx": 0,
    "dy": 0,
    "w": 390,
    "h": 1600
   },
   "alts": [],
   "css": {},
   "liveText": null,
   "bindings": {},
   "instance": null,
   "children": [
    "3.hdr",
    "3.card",
    "3.sticky",
    "3.rows",
    "3.back",
    "3.jump"
   ],
   "interactions": []
  },
  "3.hdr": {
   "id": "3.hdr",
   "name": "Header",
   "kind": "leaf",
   "x": 0,
   "y": 0,
   "w": 390,
   "h": 64,
   "rotation": 0,
   "opacity": 1,
   "visible": true,
   "clip": false,
   "overflow": "none",
   "position": "fixed",
   "paint": {
    "src": "assets/header.svg",
    "dx": 0,
    "dy": 0,
    "w": 390,
    "h": 64
   },
   "alts": [],
   "css": {},
   "liveText": null,
   "bindings": {},
   "instance": null,
   "children": [],
   "interactions": []
  },
  "3.card": {
   "id": "3.card",
   "name": "Card",
   "kind": "leaf",
   "x": 25,
   "y": 90,
   "w": 300,
   "h": 120,
   "rotation": 0,
   "opacity": 1,
   "visible": true,
   "clip": false,
   "overflow": "none",
   "position": "scroll",
   "paint": {
    "src": "assets/card_a.svg",
    "dx": 0,
    "dy": 0,
    "w": 300,
    "h": 120
   },
   "alts": [],
   "css": {},
   "liveText": null,
   "bindings": {},
   "instance": null,
   "children": [],
   "interactions": []
  },
  "3.row0": {
   "id": "3.row0",
   "name": "Ligne 1",
   "kind": "leaf",
   "x": 25,
   "y": 240,
   "w": 340,
   "h": 80,
   "rotation": 0,
   "opacity": 1,
   "visible": true,
   "clip": false,
   "overflow": "none",
   "position": "scroll",
   "paint": {
    "src": "assets/row.svg",
    "dx": 0,
    "dy": 0,
    "w": 340,
    "h": 80
   },
   "alts": [],
   "css": {},
   "liveText": null,
   "bindings": {},
   "instance": null,
   "children": [],
   "interactions": []
  },
  "3.row1": {
   "id": "3.row1",
   "name": "Ligne 2",
   "kind": "leaf",
   "x": 25,
   "y": 340,
   "w": 340,
   "h": 80,
   "rotation": 0,
   "opacity": 1,
   "visible": true,
   "clip": false,
   "overflow": "none",
   "position": "scroll",
   "paint": {
    "src": "assets/row.svg",
    "dx": 0,
    "dy": 0,
    "w": 340,
    "h": 80
   },
   "alts": [],
   "css": {},
   "liveText": null,
   "bindings": {},
   "instance": null,
   "children": [],
   "interactions": []
  },
  "3.row2": {
   "id": "3.row2",
   "name": "Ligne 3",
   "kind": "leaf",
   "x": 25,
   "y": 440,
   "w": 340,
   "h": 80,
   "rotation": 0,
   "opacity": 1,
   "visible": true,
   "clip": false,
   "overflow": "none",
   "position": "scroll",
   "paint": {
    "src": "assets/row.svg",
    "dx": 0,
    "dy": 0,
    "w": 340,
    "h": 80
   },
   "alts": [],
   "css": {},
   "liveText": null,
   "bindings": {},
   "instance": null,
   "children": [],
   "interactions": []
  },
  "3.row3": {
   "id": "3.row3",
   "name": "Ligne 4",
   "kind": "leaf",
   "x": 25,
   "y": 540,
   "w": 340,
   "h": 80,
   "rotation": 0,
   "opacity": 1,
   "visible": true,
   "clip": false,
   "overflow": "none",
   "position": "scroll",
   "paint": {
    "src": "assets/row.svg",
    "dx": 0,
    "dy": 0,
    "w": 340,
    "h": 80
   },
   "alts": [],
   "css": {},
   "liveText": null,
   "bindings": {},
   "instance": null,
   "children": [],
   "interactions": []
  },
  "3.row4": {
   "id": "3.row4",
   "name": "Ligne 5",
   "kind": "leaf",
   "x": 25,
   "y": 640,
   "w": 340,
   "h": 80,
   "rotation": 0,
   "opacity": 1,
   "visible": true,
   "clip": false,
   "overflow": "none",
   "position": "scroll",
   "paint": {
    "src": "assets/row.svg",
    "dx": 0,
    "dy": 0,
    "w": 340,
    "h": 80
   },
   "alts": [],
   "css": {},
   "liveText": null,
   "bindings": {},
   "instance": null,
   "children": [],
   "interactions": []
  },
  "3.row5": {
   "id": "3.row5",
   "name": "Ligne 6",
   "kind": "leaf",
   "x": 25,
   "y": 740,
   "w": 340,
   "h": 80,
   "rotation": 0,
   "opacity": 1,
   "visible": true,
   "clip": false,
   "overflow": "none",
   "position": "scroll",
   "paint": {
    "src": "assets/row.svg",
    "dx": 0,
    "dy": 0,
    "w": 340,
    "h": 80
   },
   "alts": [],
   "css": {},
   "liveText": null,
   "bindings": {},
   "instance": null,
   "children": [],
   "interactions": []
  },
  "3.row6": {
   "id": "3.row6",
   "name": "Ligne 7",
   "kind": "leaf",
   "x": 25,
   "y": 840,
   "w": 340,
   "h": 80,
   "rotation": 0,
   "opacity": 1,
   "visible": true,
   "clip": false,
   "overflow": "none",
   "position": "scroll",
   "paint": {
    "src": "assets/row.svg",
    "dx": 0,
    "dy": 0,
    "w": 340,
    "h": 80
   },
   "alts": [],
   "css": {},
   "liveText": null,
   "bindings": {},
   "instance": null,
   "children": [],
   "interactions": []
  },
  "3.row7": {
   "id": "3.row7",
   "name": "Ligne 8",
   "kind": "leaf",
   "x": 25,
   "y": 940,
   "w": 340,
   "h": 80,
   "rotation": 0,
   "opacity": 1,
   "visible": true,
   "clip": false,
   "overflow": "none",
   "position": "scroll",
   "paint": {
    "src": "assets/row.svg",
    "dx": 0,
    "dy": 0,
    "w": 340,
    "h": 80
   },
   "alts": [],
   "css": {},
   "liveText": null,
   "bindings": {},
   "instance": null,
   "children": [],
   "interactions": []
  },
  "3.rows": {
   "id": "3.rows",
   "name": "Lignes",
   "kind": "group",
   "x": 0,
   "y": 0,
   "w": 390,
   "h": 1600,
   "rotation": 0,
   "opacity": 1,
   "visible": true,
   "clip": false,
   "overflow": "none",
   "position": "scroll",
   "paint": null,
   "alts": [],
   "css": {},
   "liveText": null,
   "bindings": {},
   "instance": null,
   "children": [
    "3.row0",
    "3.row1",
    "3.row2",
    "3.row3",
    "3.row4",
    "3.row5",
    "3.row6",
    "3.row7"
   ],
   "interactions": []
  },
  "3.back": {
   "id": "3.back",
   "name": "Retour",
   "kind": "leaf",
   "x": 25,
   "y": 780,
   "w": 120,
   "h": 40,
   "rotation": 0,
   "opacity": 1,
   "visible": true,
   "clip": false,
   "overflow": "none",
   "position": "fixed",
   "paint": {
    "src": "assets/btn_back.svg",
    "dx": 0,
    "dy": 0,
    "w": 120,
    "h": 40
   },
   "alts": [],
   "css": {},
   "liveText": null,
   "bindings": {},
   "instance": null,
   "children": [],
   "interactions": [
    {
     "trigger": {
      "type": "click"
     },
     "actions": [
      {
       "type": "navigate",
       "dest": "1",
       "transition": {
        "type": "slideIn",
        "durationMs": 300,
        "easing": {
         "type": "easeInOut"
        },
        "direction": "left"
       }
      }
     ]
    }
   ]
  },
  "4": {
   "id": "4",
   "name": "Menu overlay",
   "kind": "frame",
   "x": 0,
   "y": 0,
   "w": 260,
   "h": 300,
   "rotation": 0,
   "opacity": 1,
   "visible": true,
   "clip": false,
   "overflow": "none",
   "position": "scroll",
   "paint": {
    "src": "assets/overlay_bg.svg",
    "dx": 0,
    "dy": 0,
    "w": 260,
    "h": 300
   },
   "alts": [],
   "css": {},
   "liveText": null,
   "bindings": {},
   "instance": null,
   "children": [
    "4.swap",
    "4.link",
    "4.close"
   ],
   "interactions": []
  },
  "4.close": {
   "id": "4.close",
   "name": "Fermer",
   "kind": "leaf",
   "x": 70,
   "y": 240,
   "w": 120,
   "h": 40,
   "rotation": 0,
   "opacity": 1,
   "visible": true,
   "clip": false,
   "overflow": "none",
   "position": "scroll",
   "paint": {
    "src": "assets/overlay_close.svg",
    "dx": 0,
    "dy": 0,
    "w": 120,
    "h": 40
   },
   "alts": [],
   "css": {},
   "liveText": null,
   "bindings": {},
   "instance": null,
   "children": [],
   "interactions": [
    {
     "trigger": {
      "type": "click"
     },
     "actions": [
      {
       "type": "closeOverlay"
      }
     ]
    }
   ]
  },
  "1.badge": {
   "id": "1.badge",
   "name": "Badge",
   "kind": "leaf",
   "x": 270,
   "y": 86,
   "w": 90,
   "h": 32,
   "rotation": -12,
   "opacity": 0.85,
   "visible": true,
   "clip": false,
   "overflow": "none",
   "position": "scroll",
   "paint": {
    "src": "assets/badge.svg",
    "dx": 0,
    "dy": 0,
    "w": 90,
    "h": 32
   },
   "alts": [],
   "css": {},
   "liveText": null,
   "bindings": {
    "visible": "v.badge"
   },
   "instance": null,
   "children": [],
   "interactions": []
  },
  "2.fuzzy": {
   "id": "2.fuzzy",
   "name": "Flou",
   "kind": "leaf",
   "x": 25,
   "y": 440,
   "w": 340,
   "h": 80,
   "rotation": 0,
   "opacity": 1,
   "visible": true,
   "clip": false,
   "overflow": "none",
   "position": "scroll",
   "paint": {
    "src": "assets/fuzzy.svg",
    "dx": 0,
    "dy": 0,
    "w": 340,
    "h": 80
   },
   "alts": [],
   "css": {
    "layerBlur": 3
   },
   "liveText": null,
   "bindings": {},
   "instance": null,
   "children": [],
   "interactions": []
  },
  "2.drag": {
   "id": "2.drag",
   "name": "Glisser",
   "kind": "leaf",
   "x": 25,
   "y": 560,
   "w": 340,
   "h": 80,
   "rotation": 0,
   "opacity": 1,
   "visible": true,
   "clip": false,
   "overflow": "none",
   "position": "scroll",
   "paint": {
    "src": "assets/drag.svg",
    "dx": 0,
    "dy": 0,
    "w": 340,
    "h": 80
   },
   "alts": [],
   "css": {},
   "liveText": null,
   "bindings": {},
   "instance": null,
   "children": [],
   "interactions": [
    {
     "trigger": {
      "type": "drag"
     },
     "actions": [
      {
       "type": "navigate",
       "dest": "3",
       "transition": {
        "type": "push",
        "durationMs": 400,
        "easing": {
         "type": "easeOut"
        },
        "direction": "left"
       }
      }
     ]
    }
   ]
  },
  "3.sticky": {
   "id": "3.sticky",
   "name": "Sous-titre",
   "kind": "leaf",
   "x": 0,
   "y": 212,
   "w": 390,
   "h": 28,
   "rotation": 0,
   "opacity": 1,
   "visible": true,
   "clip": false,
   "overflow": "none",
   "position": "sticky",
   "paint": {
    "src": "assets/sticky.svg",
    "dx": 0,
    "dy": 0,
    "w": 390,
    "h": 28
   },
   "alts": [],
   "css": {},
   "liveText": null,
   "bindings": {},
   "instance": null,
   "children": [],
   "interactions": []
  },
  "3.jump": {
   "id": "3.jump",
   "name": "Aller à la ligne 6",
   "kind": "leaf",
   "x": 205,
   "y": 780,
   "w": 160,
   "h": 40,
   "rotation": 0,
   "opacity": 1,
   "visible": true,
   "clip": false,
   "overflow": "none",
   "position": "fixed",
   "paint": {
    "src": "assets/jump.svg",
    "dx": 0,
    "dy": 0,
    "w": 160,
    "h": 40
   },
   "alts": [],
   "css": {},
   "liveText": null,
   "bindings": {},
   "instance": null,
   "children": [],
   "interactions": [
    {
     "trigger": {
      "type": "click"
     },
     "actions": [
      {
       "type": "scrollTo",
       "dest": "3.row5",
       "offset": [
        0,
        72
       ],
       "transition": {
        "type": "smartAnimate",
        "durationMs": 500,
        "easing": {
         "type": "easeInOut"
        }
       }
      }
     ]
    }
   ]
  },
  "4.swap": {
   "id": "4.swap",
   "name": "Autre menu",
   "kind": "leaf",
   "x": 50,
   "y": 120,
   "w": 160,
   "h": 40,
   "rotation": 0,
   "opacity": 1,
   "visible": true,
   "clip": false,
   "overflow": "none",
   "position": "scroll",
   "paint": {
    "src": "assets/swap.svg",
    "dx": 0,
    "dy": 0,
    "w": 160,
    "h": 40
   },
   "alts": [],
   "css": {},
   "liveText": null,
   "bindings": {},
   "instance": null,
   "children": [],
   "interactions": [
    {
     "trigger": {
      "type": "click"
     },
     "actions": [
      {
       "type": "swapOverlay",
       "dest": "5",
       "position": "bottomCenter",
       "closeOnClickOutside": true,
       "background": "rgba(0,0,0,0.4)",
       "transition": {
        "type": "moveIn",
        "durationMs": 300,
        "easing": {
         "type": "easeOut"
        },
        "direction": "top"
       }
      }
     ]
    }
   ]
  },
  "4.link": {
   "id": "4.link",
   "name": "Lien",
   "kind": "leaf",
   "x": 50,
   "y": 180,
   "w": 160,
   "h": 40,
   "rotation": 0,
   "opacity": 1,
   "visible": true,
   "clip": false,
   "overflow": "none",
   "position": "scroll",
   "paint": {
    "src": "assets/link.svg",
    "dx": 0,
    "dy": 0,
    "w": 160,
    "h": 40
   },
   "alts": [],
   "css": {},
   "liveText": null,
   "bindings": {},
   "instance": null,
   "children": [],
   "interactions": [
    {
     "trigger": {
      "type": "click"
     },
     "actions": [
      {
       "type": "openUrl",
       "url": "https://example.com/",
       "newTab": true
      }
     ]
    }
   ]
  },
  "5": {
   "id": "5",
   "name": "Second menu",
   "kind": "frame",
   "x": 0,
   "y": 0,
   "w": 300,
   "h": 180,
   "rotation": 0,
   "opacity": 1,
   "visible": true,
   "clip": true,
   "overflow": "none",
   "position": "scroll",
   "paint": {
    "src": "assets/overlay2_bg.svg",
    "dx": 0,
    "dy": 0,
    "w": 300,
    "h": 180
   },
   "alts": [],
   "css": {},
   "liveText": null,
   "bindings": {},
   "instance": null,
   "children": [
    "5.close"
   ],
   "interactions": [
    {
     "trigger": {
      "type": "afterDelay",
      "delayMs": 3000
     },
     "actions": [
      {
       "type": "closeOverlay"
      }
     ]
    }
   ]
  },
  "5.close": {
   "id": "5.close",
   "name": "Fermer",
   "kind": "leaf",
   "x": 90,
   "y": 110,
   "w": 120,
   "h": 40,
   "rotation": 0,
   "opacity": 1,
   "visible": true,
   "clip": false,
   "overflow": "none",
   "position": "scroll",
   "paint": {
    "src": "assets/overlay_close.svg",
    "dx": 0,
    "dy": 0,
    "w": 120,
    "h": 40
   },
   "alts": [],
   "css": {},
   "liveText": null,
   "bindings": {},
   "instance": null,
   "children": [],
   "interactions": [
    {
     "trigger": {
      "type": "click"
     },
     "actions": [
      {
       "type": "closeOverlay"
      }
     ]
    }
   ]
  }
 },
 "variables": {
  "collections": {
   "c.theme": {
    "name": "Theme",
    "defaultMode": "m.light",
    "modes": {
     "m.light": "Light",
     "m.dark": "Dark"
    }
   }
  },
  "vars": {
   "v.count": {
    "name": "count",
    "collection": "c.theme",
    "type": "number",
    "valuesByMode": {
     "m.light": 0,
     "m.dark": 0
    }
   },
   "v.mode": {
    "name": "mode",
    "collection": "c.theme",
    "type": "string",
    "valuesByMode": {
     "m.light": "Light",
     "m.dark": "Light"
    }
   },
   "v.surface": {
    "name": "surface",
    "collection": "c.theme",
    "type": "color",
    "valuesByMode": {
     "m.light": "#ffffff",
     "m.dark": "#1c1c28"
    }
   },
   "v.badge": {
    "name": "badge",
    "collection": "c.theme",
    "type": "boolean",
    "valuesByMode": {
     "m.light": false,
     "m.dark": false
    }
   }
  }
 },
 "report": {
  "approximated": [
   "Verre: flou d'arrière-plan approximé en CSS"
  ],
  "skipped": []
 }
};
