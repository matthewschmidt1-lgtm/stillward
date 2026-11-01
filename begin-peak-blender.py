import bpy, bmesh, math, sys
from mathutils import Vector, noise

out = sys.argv[sys.argv.index('--') + 1]
W, H = 1360, 224            # 4x of 340x56
SAMPLES = 96

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

SX, SY = 6.8, 1.12          # plane size, same aspect as the button
NX, NY = 680, 112

# --- terrain -------------------------------------------------------------
mesh = bpy.data.meshes.new('peak')
obj = bpy.data.objects.new('peak', mesh)
scene.collection.objects.link(obj)
bm = bmesh.new()
bmesh.ops.create_grid(bm, x_segments=NX, y_segments=NY, size=1.0)
PX, PY = -0.15, 0.02        # summit position

def ridged(p, octaves=5):
    v, amp, freq, tot = 0.0, 1.0, 1.0, 0.0
    for _ in range(octaves):
        n = 1.0 - abs(noise.noise(p * freq))
        v += n * n * amp
        tot += amp
        amp *= 0.5
        freq *= 2.1
    return v / tot

import random
random.seed(21)
# ridge crest lines in squashed space (x, y*2): (x0,y0,h0) -> (x1,y1,h1)
SUM = (PX, PY * 2.0, 1.0)
ridges = []
angs = [8, 52, 100, 148, 190, 232, 276, 322]
for a in angs:
    a = math.radians(a + random.uniform(-9, 9))
    L = random.uniform(2.2, 3.2)
    end = (SUM[0] + math.cos(a) * L, SUM[1] + math.sin(a) * L * 0.8, random.uniform(0.02, 0.18))
    ridges.append((SUM, end))
    # a side ridge branching from the middle of this one
    mid = ((SUM[0] + end[0]) / 2, (SUM[1] + end[1]) / 2, (SUM[2] + end[2]) / 2 * 0.95)
    b2 = a + math.radians(random.choice([-1, 1]) * random.uniform(28, 48))
    L2 = random.uniform(0.9, 1.5)
    ridges.append((mid, (mid[0] + math.cos(b2) * L2, mid[1] + math.sin(b2) * L2 * 0.8, random.uniform(0.0, 0.1))))
    q = (SUM[0] + (end[0] - SUM[0]) * 0.72, SUM[1] + (end[1] - SUM[1]) * 0.72, 0.3 * (1 - 0.72) + 0.06)
    b3 = a - math.radians(random.choice([-1, 1]) * random.uniform(24, 40))
    ridges.append((q, (q[0] + math.cos(b3) * 0.8, q[1] + math.sin(b3) * 0.65, 0.02)))

def tent(px, py, seg, k):
    (x0, y0, h0), (x1, y1, h1) = seg
    vx, vy = x1 - x0, y1 - y0
    l2 = vx * vx + vy * vy
    t = max(0.0, min(1.0, ((px - x0) * vx + (py - y0) * vy) / l2))
    qx, qy = x0 + vx * t, y0 + vy * t
    d = math.hypot(px - qx, py - qy)
    hz = h0 + (h1 - h0) * (t ** 0.85)
    return hz - k * d

hmax = -9
for vert in bm.verts:
    x = vert.co.x * SX / 2
    y = vert.co.y * SY / 2
    px, py = x, y * 2.0
    # gentle domain warp for jagged crests
    wx = px + noise.noise(Vector((px * 1.6, py * 1.6, 1.0))) * 0.30
    wy = py + noise.noise(Vector((px * 1.6, py * 1.6, 5.0))) * 0.30
    wx += noise.noise(Vector((px * 4.5, py * 4.5, 3.0))) * 0.07
    wy += noise.noise(Vector((px * 4.5, py * 4.5, 7.0))) * 0.07
    h = max(tent(wx, wy, sg, 0.9) for sg in ridges)
    rr = math.hypot(px - PX, (py - PY * 2.0) * 0.8) / 3.6
    mound = 0.30 * max(0.0, 1.0 - rr) ** 0.9 + 0.10 + 0.06 * noise.noise(Vector((px * 0.9, py * 0.9, 2.0)))
    h = max(h, mound)
    h += noise.noise(Vector((x * 3.0, y * 6.0, 9.0))) * 0.018 * min(1.0, h * 3)
    hmax = max(hmax, h)
    vert.co.x, vert.co.y, vert.co.z = x, y, h
bm.to_mesh(mesh)
bm.free()
for p in mesh.polygons:
    p.use_smooth = True

# --- material: sage rock, snow near the summit ---------------------------
mat = bpy.data.materials.new('rock')
mat.use_nodes = True
nt = mat.node_tree
nt.nodes.clear()
out_n = nt.nodes.new('ShaderNodeOutputMaterial')
bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
geo = nt.nodes.new('ShaderNodeNewGeometry')
sep = nt.nodes.new('ShaderNodeSeparateXYZ')
ramp = nt.nodes.new('ShaderNodeValToRGB')
tex = nt.nodes.new('ShaderNodeTexNoise')
mix = nt.nodes.new('ShaderNodeMixRGB')
mapr = nt.nodes.new('ShaderNodeMapRange')
texco = nt.nodes.new('ShaderNodeTexCoord')
nt.links.new(texco.outputs['Object'], sep.inputs[0])
nt.links.new(sep.outputs['Z'], mapr.inputs['Value'])
mapr.inputs['From Min'].default_value = 0.0
mapr.inputs['From Max'].default_value = 0.95
nt.links.new(texco.outputs['Object'], tex.inputs['Vector'])
tex.inputs['Scale'].default_value = 45
tex.inputs['Detail'].default_value = 8
mix.blend_type = 'MIX'
mix.inputs['Fac'].default_value = 0.10
nt.links.new(mapr.outputs['Result'], ramp.inputs['Fac'])
nt.links.new(ramp.outputs['Color'], mix.inputs['Color1'])
nt.links.new(tex.outputs['Color'], mix.inputs['Color2'])
nt.links.new(mix.outputs['Color'], bsdf.inputs['Base Color'])
nt.links.new(bsdf.outputs['BSDF'], out_n.inputs['Surface'])
bsdf.inputs['Roughness'].default_value = 0.85
e = ramp.color_ramp.elements
e[0].position, e[0].color = 0.00, (0.44, 0.62, 0.51, 1)
e[1].position, e[1].color = 1.00, (0.97, 0.99, 0.98, 1)
e2 = e.new(0.30); e2.color = (0.60, 0.76, 0.66, 1)
e3 = e.new(0.58); e3.color = (0.80, 0.90, 0.85, 1)
e4 = e.new(0.80); e4.color = (0.95, 0.98, 0.96, 1)
obj.data.materials.append(mat)

# --- light, camera, world ------------------------------------------------
sun = bpy.data.lights.new('sun', 'SUN')
sun.energy = 2.3
sun.angle = math.radians(14)             # soft shadows
sun.color = (1.0, 0.98, 0.94)
sun_o = bpy.data.objects.new('sun', sun)
sun_o.rotation_euler = (math.radians(48), math.radians(0), math.radians(-45))
scene.collection.objects.link(sun_o)

world = bpy.data.worlds.new('w')
world.use_nodes = True
bg = world.node_tree.nodes['Background']
bg.inputs['Color'].default_value = (0.62, 0.84, 0.70, 1)
bg.inputs['Strength'].default_value = 0.55
scene.world = world

cam = bpy.data.cameras.new('cam')
cam.type = 'ORTHO'
cam.ortho_scale = SX
cam_o = bpy.data.objects.new('cam', cam)
cam_o.location = (0, 0, 5)
scene.collection.objects.link(cam_o)
scene.camera = cam_o

scene.render.engine = 'CYCLES'
scene.cycles.samples = SAMPLES
scene.cycles.use_denoising = True
scene.cycles.device = 'CPU'
scene.render.resolution_x = W
scene.render.resolution_y = H
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = 'Standard'
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = out
print('HMAX', hmax)
bpy.ops.render.render(write_still=True)
