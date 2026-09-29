import re

file_path = "/Users/srisaran/Quads/frontend/webapp/css/style.css"
with open(file_path, "r") as f:
    content = f.read()

start_str = "/* NEW HORIZONTAL TIMELINE STEPPER */"
start_idx = content.find(start_str)

if start_idx != -1:
    css_new = """/* NEW HORIZONTAL TIMELINE STEPPER */
.quadsTimelineScroll {
    flex: 1;
    overflow-x: auto;
    overflow-y: hidden;
}
.quadsTimelineFlexRow {
    display: flex;
    min-width: 720px;
    padding: 10px 0;
    width: 100%;
}
.quadsTimelineItem {
    flex: 1;
    position: relative;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    min-width: 0;
    text-align: center;
}
/* Connecting line via pseudo-element */
.quadsTimelineItem:not(:last-child)::after {
    content: "";
    position: absolute;
    top: 16px;
    left: calc(50% + 16px);
    right: calc(-50% + 16px);
    height: 2px;
    background-color: #D1D5DB; /* light grey line */
    z-index: 0;
}
.quadsTimelineItem.completed::after {
    background-color: #16A34A; /* green line after it */
}

/* Circle */
.quadsTimelineCircleBox {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    z-index: 1;
    background-color: #E5E7EB; /* Not completed fill */
    margin-bottom: 8px;
    box-sizing: border-box;
    display: flex;
    align-items: center;
    justify-content: center;
}

/* Completed */
.quadsTimelineItem.completed .quadsTimelineCircleBox {
    background-color: #16A34A; /* solid green fill */
}
/* Current */
.quadsTimelineItem.current .quadsTimelineCircleBox {
    background-color: #0070F2; /* solid blue fill */
}
/* Current + Completed */
.quadsTimelineItem.current-completed .quadsTimelineCircleBox {
    background-color: #16A34A; /* green fill */
    box-shadow: 0 0 0 3px #0070F2; /* 3px blue outer ring */
}

/* Numbers inside circle */
.quadsTimelineText {
    color: #4B5563; /* dark grey number */
    font-size: 14px;
    font-weight: 700;
}
.quadsTimelineItem.completed .quadsTimelineText {
    display: none; /* replaced by icon */
}
.quadsTimelineItem.current .quadsTimelineText {
    color: #FFFFFF; /* white number */
}

/* Tick Icon */
.quadsTimelineIcon {
    color: #FFFFFF !important;
    font-size: 14px !important;
}

/* Labels */
.quadsTimelineLabel {
    font-size: 13px;
    color: #4B5563; /* grey label */
    text-align: center;
    line-height: 1.2;
    white-space: normal;
    word-break: normal;
    overflow-wrap: normal;
    hyphens: none;
}
.quadsTimelineItem.completed .quadsTimelineLabel {
    color: #16A34A; /* green bold label */
    font-weight: 700;
}
.quadsTimelineItem.current .quadsTimelineLabel,
.quadsTimelineItem.current-completed .quadsTimelineLabel {
    color: #0070F2; /* blue bold label */
    font-weight: 700;
}
"""
    new_content = content[:start_idx] + css_new
    with open(file_path, "w") as f:
        f.write(new_content)
    print("Replaced CSS block")
else:
    print("Could not find CSS block")
