import tkinter as tk
from tkinter import filedialog, Label, Button, Frame, messagebox
from PIL import Image, ImageTk
import numpy as np
import os
from tensorflow import keras

class PainterClassifierApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Painter Classifier")
        self.root.geometry("500x600")
        self.root.configure(bg="#f0f0f0")
        
        # Try to load the trained model
        try:
            # Try different possible model filenames - keeping your original paths
            model_files = ["modellen/fine_tuned_model.keras", "convnet_from_scratch_with_augmentation.keras", 
                          "convnet_from_scratch.keras", "transfer_model.keras"]
            
            self.model = None
            for model_file in model_files:
                if os.path.exists(model_file):
                    print(f"Loading model from {model_file}")
                    self.model = keras.models.load_model(model_file)
                    break
            
            if self.model is None:
                print("No model file found. Will need to specify model file later.")
        except Exception as e:
            print(f"Error loading model: {e}")
            self.model = None
        
        # Set up the UI
        self.setup_ui()
        
        # Initialize variables
        self.image_path = None
        self.display_image = None
        
    def setup_ui(self):
        # Main frame
        main_frame = Frame(self.root, bg="#f0f0f0")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title = Label(main_frame, text="Mondriaan or Picasso Classifier", 
                     font=("Arial", 16, "bold"), bg="#f0f0f0")
        title.pack(pady=10)
        
        # Frame for image
        image_frame = Frame(main_frame, bg="white", width=300, height=300,
                           highlightbackground="gray", highlightthickness=1)
        image_frame.pack(pady=10)
        image_frame.pack_propagate(False)  # Prevent frame from shrinking
        
        # Image display area
        self.image_label = Label(image_frame, bg="white")
        self.image_label.pack(expand=True, fill="both")
        
        # Button frame
        button_frame = Frame(main_frame, bg="#f0f0f0")
        button_frame.pack(pady=10)
        
        # Select image button - ENSURE THIS IS VISIBLE
        select_btn = Button(button_frame, text="Select Image", command=self.select_image,
                           font=("Arial", 12), bg="#4CAF50", fg="white", padx=10)
        select_btn.pack(side=tk.LEFT, padx=5)
        
        # Predict button
        predict_btn = Button(button_frame, text="Predict Painter", command=self.predict_image,
                            font=("Arial", 12), bg="#2196F3", fg="white", padx=10)
        predict_btn.pack(side=tk.LEFT, padx=5)
        
        # Result frame
        result_frame = Frame(main_frame, bg="#f0f0f0")
        result_frame.pack(pady=10, fill="x")
        
        # Result display
        self.result_label = Label(result_frame, text="Select an image and click Predict", 
                                 font=("Arial", 14), bg="#f0f0f0")
        self.result_label.pack(pady=5)
        
        # Confidence display
        self.confidence_label = Label(result_frame, text="", 
                                     font=("Arial", 12), bg="#f0f0f0")
        self.confidence_label.pack(pady=5)
        
        # Status bar
        self.status_bar = Label(self.root, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # If no model is loaded, show a warning
        if self.model is None:
            self.status_bar.config(text="Warning: No model loaded. Select model file before prediction.")
    
    def select_image(self):
        # Open file dialog to select an image
        self.image_path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=(("Image files", "*.jpg *.jpeg *.png"), ("All files", "*.*"))
        )
        
        if self.image_path:
            try:
                # Update status bar
                self.status_bar.config(text=f"Selected: {os.path.basename(self.image_path)}")
                
                # Display the selected image
                img = Image.open(self.image_path)
                
                # Calculate aspect ratio to maintain proportions
                width, height = img.size
                max_size = 290  # Slightly smaller than the frame
                
                # Resize while maintaining aspect ratio
                if width > height:
                    new_width = max_size
                    new_height = int(height * (max_size / width))
                else:
                    new_height = max_size
                    new_width = int(width * (max_size / height))
                
                img = img.resize((new_width, new_height), Image.LANCZOS)
                self.display_image = ImageTk.PhotoImage(img)
                self.image_label.configure(image=self.display_image)
                
                # Clear previous prediction
                self.result_label.configure(text="Ready to predict")
                self.confidence_label.configure(text="")
            except Exception as e:
                self.status_bar.config(text=f"Error loading image: {str(e)}")
                messagebox.showerror("Error", f"Failed to load image: {str(e)}")
    
    def predict_image(self):
        if not self.image_path:
            self.result_label.configure(text="Please select an image first!")
            messagebox.showinfo("Info", "Please select an image first!")
            return
        
        if self.model is None:
            # If no model is loaded, ask to select model file
            model_path = filedialog.askopenfilename(
                title="Select Model File",
                filetypes=(("Keras models", "*.keras"), ("All files", "*.*"))
            )
            if model_path:
                try:
                    self.model = keras.models.load_model(model_path)
                    self.status_bar.config(text=f"Model loaded: {os.path.basename(model_path)}")
                except Exception as e:
                    self.status_bar.config(text=f"Error loading model: {str(e)}")
                    messagebox.showerror("Error", f"Failed to load model: {str(e)}")
                    return
            else:
                return
        
        try:
            # Update status
            self.status_bar.config(text="Analyzing image...")
            self.root.update()
            
            # Handle both keras.preprocessing and keras.utils (for compatibility)
            try:
                # Try the original method first
                img = keras.preprocessing.image.load_img(
                    self.image_path, target_size=(180, 180)
                )
                img_array = keras.preprocessing.image.img_to_array(img)
            except AttributeError:
                # Fall back to keras.utils if preprocessing is not available
                img = keras.utils.load_img(
                    self.image_path, target_size=(180, 180)
                )
                img_array = keras.utils.img_to_array(img)
            
            img_array = np.expand_dims(img_array, axis=0)
            
            # Make prediction
            prediction = self.model.predict(img_array)[0][0]
            
            # Determine the class (Mondriaan or Picasso)
            painter = "Picasso" if prediction > 0.5 else "Mondriaan"
            confidence = prediction if prediction > 0.5 else 1 - prediction
            
            # Update the UI with the prediction
            self.result_label.configure(text=f"Predicted Painter: {painter}")
            self.confidence_label.configure(text=f"Confidence: {confidence:.2%}")
            self.status_bar.config(text="Prediction complete")
        except Exception as e:
            self.status_bar.config(text=f"Error during prediction: {str(e)}")
            messagebox.showerror("Error", f"Prediction error: {str(e)}")
            print(f"Prediction error: {str(e)}")

# Create the app
if __name__ == "__main__":
    root = tk.Tk()
    app = PainterClassifierApp(root)
    root.mainloop()