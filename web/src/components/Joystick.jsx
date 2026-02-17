import { useRef, useEffect, useCallback } from 'react'

const KNOB_RADIUS = 30
const DEAD_ZONE = 5

export default function Joystick({ size = 220, onMove, onRelease }) {
    const canvasRef = useRef(null)
    const knobPos = useRef({ x: 0, y: 0 })
    const isDragging = useRef(false)
    const animFrame = useRef(null)
    const lastEmit = useRef(0)

    const baseRadius = size / 2 - 4
    const center = size / 2

    const draw = useCallback(() => {
        const canvas = canvasRef.current
        if (!canvas) return
        const ctx = canvas.getContext('2d')
        const dpr = window.devicePixelRatio || 1
        const w = size * dpr
        ctx.clearRect(0, 0, w, w)
        ctx.save()
        ctx.scale(dpr, dpr)

        const cx = center
        const cy = center
        const kx = cx + knobPos.current.x
        const ky = cy + knobPos.current.y

        // Outer ring
        ctx.beginPath()
        ctx.arc(cx, cy, baseRadius, 0, Math.PI * 2)
        ctx.strokeStyle = 'rgba(99, 102, 241, 0.15)'
        ctx.lineWidth = 2
        ctx.stroke()

        // Inner guides — crosshair
        ctx.beginPath()
        ctx.moveTo(cx, cy - baseRadius + 10)
        ctx.lineTo(cx, cy + baseRadius - 10)
        ctx.strokeStyle = 'rgba(99, 102, 241, 0.06)'
        ctx.lineWidth = 1
        ctx.stroke()

        ctx.beginPath()
        ctx.moveTo(cx - baseRadius + 10, cy)
        ctx.lineTo(cx + baseRadius - 10, cy)
        ctx.stroke()

        // Direction arrows
        const arrowSize = 8
        const arrowDist = baseRadius - 18
        ctx.fillStyle = 'rgba(99, 102, 241, 0.15)'
        // Up arrow
        ctx.beginPath()
        ctx.moveTo(cx, cy - arrowDist)
        ctx.lineTo(cx - arrowSize, cy - arrowDist + arrowSize + 2)
        ctx.lineTo(cx + arrowSize, cy - arrowDist + arrowSize + 2)
        ctx.fill()
        // Down arrow
        ctx.beginPath()
        ctx.moveTo(cx, cy + arrowDist)
        ctx.lineTo(cx - arrowSize, cy + arrowDist - arrowSize - 2)
        ctx.lineTo(cx + arrowSize, cy + arrowDist - arrowSize - 2)
        ctx.fill()
        // Left arrow
        ctx.beginPath()
        ctx.moveTo(cx - arrowDist, cy)
        ctx.lineTo(cx - arrowDist + arrowSize + 2, cy - arrowSize)
        ctx.lineTo(cx - arrowDist + arrowSize + 2, cy + arrowSize)
        ctx.fill()
        // Right arrow
        ctx.beginPath()
        ctx.moveTo(cx + arrowDist, cy)
        ctx.lineTo(cx + arrowDist - arrowSize - 2, cy - arrowSize)
        ctx.lineTo(cx + arrowDist - arrowSize - 2, cy + arrowSize)
        ctx.fill()

        // Trail line
        if (isDragging.current) {
            ctx.beginPath()
            ctx.moveTo(cx, cy)
            ctx.lineTo(kx, ky)
            ctx.strokeStyle = 'rgba(99, 102, 241, 0.2)'
            ctx.lineWidth = 2
            ctx.stroke()
        }

        // Knob shadow
        const dist = Math.sqrt(knobPos.current.x ** 2 + knobPos.current.y ** 2)
        const intensity = Math.min(dist / baseRadius, 1)

        ctx.beginPath()
        ctx.arc(kx, ky, KNOB_RADIUS + 4, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(99, 102, 241, ${0.08 + intensity * 0.15})`
        ctx.fill()

        // Knob gradient
        const grad = ctx.createRadialGradient(
            kx - 6, ky - 6, 2,
            kx, ky, KNOB_RADIUS
        )
        const hue = isDragging.current
            ? `hsl(${240 - intensity * 40}, 80%, ${55 + intensity * 10}%)`
            : 'hsl(240, 60%, 50%)'
        const hueOuter = isDragging.current
            ? `hsl(${240 - intensity * 40}, 70%, ${35 + intensity * 10}%)`
            : 'hsl(240, 50%, 35%)'
        grad.addColorStop(0, hue)
        grad.addColorStop(1, hueOuter)

        ctx.beginPath()
        ctx.arc(kx, ky, KNOB_RADIUS, 0, Math.PI * 2)
        ctx.fillStyle = grad
        ctx.fill()

        // Knob ring
        ctx.arc(kx, ky, KNOB_RADIUS, 0, Math.PI * 2)
        ctx.strokeStyle = `rgba(255, 255, 255, ${0.15 + intensity * 0.2})`
        ctx.lineWidth = 1.5
        ctx.stroke()

        // Knob inner dot
        ctx.beginPath()
        ctx.arc(kx, ky, 4, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(255, 255, 255, ${0.3 + intensity * 0.3})`
        ctx.fill()

        ctx.restore()
    }, [size, center, baseRadius])

    const emitMove = useCallback(() => {
        const now = Date.now()
        if (now - lastEmit.current < 66) return // ~15 fps throttle
        lastEmit.current = now

        // User requested 180-degree rotation ("upside down")
        const xPct = Math.round((-knobPos.current.x / baseRadius) * 100)
        const yPct = Math.round((knobPos.current.y / baseRadius) * 100) // was -knobPos.y

        const x = Math.abs(xPct) < DEAD_ZONE ? 0 : xPct
        const y = Math.abs(yPct) < DEAD_ZONE ? 0 : yPct

        onMove?.({ x, y })
    }, [baseRadius, onMove])

    const getPointerPos = useCallback((e) => {
        const canvas = canvasRef.current
        if (!canvas) return { x: 0, y: 0 }
        const rect = canvas.getBoundingClientRect()
        const touch = e.touches ? e.touches[0] : e
        return {
            x: touch.clientX - rect.left - center,
            y: touch.clientY - rect.top - center,
        }
    }, [center])

    const constrainToCircle = useCallback((x, y) => {
        const dist = Math.sqrt(x * x + y * y)
        if (dist > baseRadius - KNOB_RADIUS) {
            const scale = (baseRadius - KNOB_RADIUS) / dist
            return { x: x * scale, y: y * scale }
        }
        return { x, y }
    }, [baseRadius])

    const handleStart = useCallback((e) => {
        e.preventDefault()
        isDragging.current = true
        const pos = getPointerPos(e)
        knobPos.current = constrainToCircle(pos.x, pos.y)
        emitMove()
        draw()
    }, [getPointerPos, constrainToCircle, emitMove, draw])

    const handleMove = useCallback((e) => {
        if (!isDragging.current) return
        e.preventDefault()
        const pos = getPointerPos(e)
        knobPos.current = constrainToCircle(pos.x, pos.y)
        emitMove()
        if (animFrame.current) cancelAnimationFrame(animFrame.current)
        animFrame.current = requestAnimationFrame(draw)
    }, [getPointerPos, constrainToCircle, emitMove, draw])

    const handleEnd = useCallback((e) => {
        if (!isDragging.current) return
        e.preventDefault()
        isDragging.current = false

        // Animate spring back to center
        const startX = knobPos.current.x
        const startY = knobPos.current.y
        const startTime = Date.now()
        const duration = 180

        const animate = () => {
            const elapsed = Date.now() - startTime
            const t = Math.min(elapsed / duration, 1)
            const ease = 1 - Math.pow(1 - t, 3) // ease out cubic
            knobPos.current.x = startX * (1 - ease)
            knobPos.current.y = startY * (1 - ease)
            draw()
            if (t < 1) {
                animFrame.current = requestAnimationFrame(animate)
            } else {
                knobPos.current = { x: 0, y: 0 }
                draw()
                onRelease?.()
            }
        }
        animate()
    }, [draw, onRelease])

    useEffect(() => {
        const canvas = canvasRef.current
        if (!canvas) return
        const dpr = window.devicePixelRatio || 1
        canvas.width = size * dpr
        canvas.height = size * dpr
        canvas.style.width = `${size}px`
        canvas.style.height = `${size}px`
        draw()
    }, [size, draw])

    useEffect(() => {
        // Global listeners for touch/mouse move and end
        const handleGlobalMove = (e) => handleMove(e)
        const handleGlobalEnd = (e) => handleEnd(e)

        window.addEventListener('mousemove', handleGlobalMove)
        window.addEventListener('mouseup', handleGlobalEnd)
        window.addEventListener('touchmove', handleGlobalMove, { passive: false })
        window.addEventListener('touchend', handleGlobalEnd)

        return () => {
            window.removeEventListener('mousemove', handleGlobalMove)
            window.removeEventListener('mouseup', handleGlobalEnd)
            window.removeEventListener('touchmove', handleGlobalMove)
            window.removeEventListener('touchend', handleGlobalEnd)
        }
    }, [handleMove, handleEnd])

    const xPct = Math.round((-knobPos.current.x / baseRadius) * 100)
    const yPct = Math.round((knobPos.current.y / baseRadius) * 100)

    return (
        <div className="joystick-section">
            <div className="joystick-wrapper">
                <canvas
                    ref={canvasRef}
                    className="joystick-canvas"
                    onMouseDown={handleStart}
                    onTouchStart={handleStart}
                />
            </div>
            <div className="joystick-values">
                <div className="joy-val">X: <span>{xPct}</span></div>
                <div className="joy-val">Y: <span>{yPct}</span></div>
            </div>
        </div>
    )
}
