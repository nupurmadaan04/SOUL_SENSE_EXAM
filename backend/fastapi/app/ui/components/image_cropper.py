import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk, ImageDraw

class AvatarCropper(tk.Toplevel):
    def __init__(self, parent, image_path, output_path, on_complete):
        super().__init__(parent)
        self.title("Adjust Profile Picture")
        self.geometry("600x700")
        self.configure(bg="#1E293B")
        
        self.image_path = image_path
        self.output_path = output_path
        self.on_complete = on_complete
        
        # Original Image
        self.original_image = Image.open(self.image_path)
        self.original_image.thumbnail((1000, 1000)) # Cap max size for performance
        
        # State
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.crop_size = 300 # Diameter of crop circle
        
        self._setup_ui()
        self._bind_events()
        self._draw_image()

    def _setup_ui(self):
        # Instructions
        tk.Label(
            self, text="Drag to Move • Scroll to Zoom", 
            fg="#94A3B8", bg="#1E293B", font=("Segoe UI", 10)
        ).pack(pady=10)
        
        # Canvas
        self.canvas_width = 500
        self.canvas_height = 500
        self.canvas = tk.Canvas(
            self, width=self.canvas_width, height=self.canvas_height, 
            bg="#0F172A", highlightthickness=0, cursor="fleur"
        )
        self.canvas.pack(pady=10)
        
        # Controls
        controls = tk.Frame(self, bg="#1E293B")
        controls.pack(pady=20)
        
        tk.Button(
            controls, text="Cancel", command=self.destroy,
            bg="#EF4444", fg="white", font=("Segoe UI", 10, "bold"),
            relief="flat", padx=20, pady=8
        ).pack(side="left", padx=10)
        
        tk.Button(
            controls, text="Save Profile Picture", command=self.save_crop,
            bg="#10B981", fg="white", font=("Segoe UI", 10, "bold"),
            relief="flat", padx=20, pady=8
        ).pack(side="left", padx=10)

    def _bind_events(self):
        self.canvas.bind("<ButtonPress-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel) # Windows
        self.canvas.bind("<Button-4>", self._on_mouse_wheel)   # Linux scroll up
        self.canvas.bind("<Button-5>", self._on_mouse_wheel)   # Linux scroll down

    def _on_mouse_down(self, event):
        self._last_x = event.x
        self._last_y = event.y

    def _on_mouse_drag(self, event):
        dx = event.x - self._last_x
        dy = event.y - self._last_y
        self.offset_x += dx
        self.offset_y += dy
        self._last_x = event.x
        self._last_y = event.y
        self._draw_image()

    def _on_mouse_wheel(self, event):
        # Determine scroll direction
        if event.num == 5 or event.delta < 0:
            factor = 0.9
        else:
            factor = 1.1
            
        self.scale *= factor
        # Clamp scale
        self.scale = max(0.1, min(self.scale, 5.0))
        self._draw_image()

    def _draw_image(self):
        self.canvas.delete("all")
        
        # 1. Transform Image
        w, h = self.original_image.size
        new_w = int(w * self.scale)
        new_h = int(h * self.scale)
        
        if new_w <= 0 or new_h <= 0: return # Safety
        
        resized = self.original_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        self.tk_img = ImageTk.PhotoImage(resized)
        
        # Center of canvas
        cx, cy = self.canvas_width // 2, self.canvas_height // 2
        
        # Image position based on offsets
        img_x = cx + self.offset_x
        img_y = cy + self.offset_y
        
        self.canvas.create_image(img_x, img_y, image=self.tk_img, anchor="center")
        
        # 2. Draw Dark Overlay (Mask)
        # Create a polygon that covers the whole canvas but has a hole in the middle
        # Tkinter canvases don't support "holes" easily, so we use 4 rectangles or an overlay image.
        # Simpler approach: Draw semi-transparent rectangle over everything? No, canvas doesn't support alpha shapes well.
        # Alternative: Draw a thick outline that covers the outside.
        
        r = self.crop_size / 2
        
        # Darken outside area
        overlay_color = "#000000"
        stipple = "gray50" # Simple stipple for pseudo-transparency
        
        # We can draw 4 rectangles around the circle area
        # Top
        self.canvas.create_rectangle(0, 0, self.canvas_width, cy - r, fill=overlay_color, stipple=stipple, outline="")
        # Bottom
        self.canvas.create_rectangle(0, cy + r, self.canvas_width, self.canvas_height, fill=overlay_color, stipple=stipple, outline="")
        # Left
        self.canvas.create_rectangle(0, cy - r, cx - r, cy + r, fill=overlay_color, stipple=stipple, outline="")
        # Right
        self.canvas.create_rectangle(cx + r, cy - r, self.canvas_width, cy + r, fill=overlay_color, stipple=stipple, outline="")
        
        # Crop Circle Border
        self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline="white", width=2)

    def save_crop(self):
        try:
            # 1. Create high-res canvas for result
            out_size = 512
            crop_r = self.crop_size / 2
            
            # Calculate source coordinates mapping to the center crop circle
            # Canvas Center (cx, cy) corresponds to Image Center + (offset_x, offset_y) scaled
            
            # We want to grab the pixels that are visible inside the circle (cx-r, cy-r) to (cx+r, cy+r)
            # relative to the image's current position/scale.
            
            # Create a new white image of crop size
            result = Image.new("RGBA", (out_size, out_size), (0, 0, 0, 0))
            
            # Transform original image
            w, h = self.original_image.size
            new_w = int(w * self.scale)
            new_h = int(h * self.scale)
            resized = self.original_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            # Paste resized image onto a canvas where center aligns
            # In UI: Image Center is at Canvas Center + Offset
            # Target: Image Center is at Output Center + Offset * (Ratio?) -> No, simpler logic:
            
            # Determine crop box on the RESIZED image.
            # Canvas crop center is (cx, cy)
            # Image is drawn at (cx + offset_x, cy + offset_y)
            # So Image Top-Left is at (cx + offset_x - new_w/2, cy + offset_y - new_h/2)
            
            # We want the area (cx-r, cy-r) to (cx+r, cy+r) relative to canvas.
            # Relative to Image Top-Left:
            # Crop X1 = (cx - r) - (cx + offset_x - new_w/2) = new_w/2 - r - offset_x
            # Crop Y1 = (cy - r) - (cy + offset_y - new_h/2) = new_h/2 - r - offset_y
            
            # UI Scale Ratio to Output
            # We want high res, but let's just stick to UI resolution * 1.5 for quality, or simpliest: 
            # Crop exactly what is shown on screen at 1:1 if we assume crop_size=300 is decent.
            # But let's verify. 300px is good for avatar.
            
            left = (new_w / 2) - crop_r - self.offset_x
            top = (new_h / 2) - crop_r - self.offset_y
            right = left + self.crop_size
            bottom = top + self.crop_size
            
            cropped = resized.crop((left, top, right, bottom))
            cropped = cropped.resize((out_size, out_size), Image.Resampling.LANCZOS)
            
            # Create Circular Mask
            mask = Image.new("L", (out_size, out_size), 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, out_size, out_size), fill=255)
            
            # Apply Mask
            final = Image.new("RGBA", (out_size, out_size), (0, 0, 0, 0))
            final.paste(cropped, (0, 0), mask=mask)
            
            # Save
            final.save(self.output_path, "PNG")
            
            self.on_complete()
            self.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save image: {e}")
