// PDF → 쪽마다 PNG + 한눈에 보는 모음(sheet.png). macOS 전용(PDFKit). 사용:
//   swift .claude/skills/portfolio-make-pdf/raster.swift <pdf> <출력 폴더> [배율=1.0]
// 결과: <출력 폴더>/p01.png … , sheet.png(쪽 썸네일 7열)
import Foundation
import PDFKit
import AppKit

let args = CommandLine.arguments
guard args.count >= 3, let doc = PDFDocument(url: URL(fileURLWithPath: args[1])) else {
  FileHandle.standardError.write("사용: swift raster.swift <pdf> <출력 폴더> [배율]\n".data(using: .utf8)!); exit(1)
}
let outDir = args[2]
let scale = CGFloat(Double(args.count > 3 ? args[3] : "1.0") ?? 1.0)
try? FileManager.default.createDirectory(atPath: outDir, withIntermediateDirectories: true)

func render(_ page: PDFPage, _ s: CGFloat) -> NSBitmapImageRep {
  let r = page.bounds(for: .mediaBox)
  let w = Int(r.width * s), h = Int(r.height * s)
  let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: w, pixelsHigh: h, bitsPerSample: 8, samplesPerPixel: 4,
                             hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
  let ctx = NSGraphicsContext(bitmapImageRep: rep)!
  let cg = ctx.cgContext
  cg.setFillColor(NSColor.white.cgColor); cg.fill(CGRect(x: 0, y: 0, width: w, height: h))
  cg.scaleBy(x: s, y: s)
  page.draw(with: .mediaBox, to: cg)
  return rep
}

let n = doc.pageCount
for i in 0..<n {
  let rep = render(doc.page(at: i)!, scale)
  try! rep.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: String(format: "%@/p%02d.png", outDir, i + 1)))
}

// 모음: 쪽 썸네일(폭 300px) 7열, 쪽 사이 회색 12px
let cols = min(7, max(1, n)), rows = (n + cols - 1) / cols
let first = doc.page(at: 0)!.bounds(for: .mediaBox)
let tw = 300, th = Int(Double(tw) * Double(first.height / first.width)), gap = 12
let W = cols * tw + (cols + 1) * gap, H = rows * th + (rows + 1) * gap
let sheet = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: W, pixelsHigh: H, bitsPerSample: 8, samplesPerPixel: 4,
                             hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
let sctx = NSGraphicsContext(bitmapImageRep: sheet)!
let scg = sctx.cgContext
scg.setFillColor(NSColor(white: 0.55, alpha: 1).cgColor); scg.fill(CGRect(x: 0, y: 0, width: W, height: H))
for i in 0..<n {
  let page = doc.page(at: i)!
  let r = page.bounds(for: .mediaBox)
  let c = i % cols, row = i / cols
  let x = gap + c * (tw + gap), y = H - (gap + row * (th + gap)) - th
  scg.saveGState()
  scg.setFillColor(NSColor.white.cgColor); scg.fill(CGRect(x: x, y: y, width: tw, height: th))
  scg.translateBy(x: CGFloat(x), y: CGFloat(y))
  scg.scaleBy(x: CGFloat(tw) / r.width, y: CGFloat(th) / r.height)
  page.draw(with: .mediaBox, to: scg)
  scg.restoreGState()
}
try! sheet.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: "\(outDir)/sheet.png"))
print("pages \(n) → \(outDir)")
