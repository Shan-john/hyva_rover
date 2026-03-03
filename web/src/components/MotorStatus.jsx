export default function MotorStatus({ motorA, motorB }) {
    const isPivotA = motorA.speed === 0 && motorB.speed > 0
    const isPivotB = motorB.speed === 0 && motorA.speed > 0

    return (
        <div className="motor-panel">
            <MotorCard
                label="Motor A · Left"
                motor={motorA}
                className="motor-a"
                isPivot={isPivotA}
            />
            <MotorCard
                label="Motor B · Right"
                motor={motorB}
                className="motor-b"
                isPivot={isPivotB}
            />
        </div>
    )
}

function MotorCard({ label, motor, className, isPivot }) {
    const { direction = 'stop', speed = 0 } = motor || {}
    const dirClass = direction === 'stop' ? '' : direction

    return (
        <div className={`motor-card ${className} ${isPivot ? 'pivot-mode' : ''}`}>
            <div className="motor-card-header">
                <span className="motor-label">{label}</span>
                <span className={`motor-direction-badge ${dirClass}`}>
                    {isPivot ? '○ PIVOT' : (direction === 'forward' ? '▲ FWD' : direction === 'backward' ? '▼ REV' : '■ STOP')}
                </span>
            </div>
            <div className="speed-bar-container">
                <div
                    className="speed-bar"
                    style={{ width: `${speed}%` }}
                />
            </div>
            <div>
                <span className="speed-value">{speed}</span>
                <span className="speed-unit">%</span>
            </div>
        </div>
    )
}
