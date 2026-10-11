import os
import json
import base64
from pathlib import Path
import secrets
import socket
import threading
import time
from base import Base
 
# GUI
import tkinter as tk
import tkinter.messagebox
import tkinter.filedialog
from PIL import ImageTk 

# aid
from hash_function import (
    build_login_proof,
    derive_password_key,
    hash_password,
    MAX_PASSWORD_ITERATIONS,
)
import asset

# ----CONSTANT----#
FORMAT = "utf-8"
BUFFER_SIZE = 2048
OFFSET = 10000
MAX_PORT = 55535
MAX_FILE_SIZE = 100 * 1024 * 1024
DOWNLOAD_DIR = Path(__file__).resolve().parent / "downloads"

## ====================GUI IMPLEMENT======================##


def display_noti(title, content):
    tkinter.messagebox.showinfo(title, content)


class tkinterApp(tk.Tk):
    # __init__ function for class tkinterApp
    def __init__(self, *args, **kwargs):
        # __init__ function for class Tk
        tk.Tk.__init__(self, *args, **kwargs)

        # creating a container
        container = tk.Frame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.chatroom_textCons = None

        # initializing frames to an empty array
        self.frames = {}

        # iterating through a tuple consisting
        # of the different page layouts
        for F in (StartPage, RegisterPage, LoginPage, ChatPage):
            frame = F(container, self)
            # initializing frame of that object from
            # startpage, registerpage, loginpage, chatpage respectively with
            # for loop
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="nsew")
            frame.configure(bg='white')
        self.show_frame(StartPage)

    # to display the current frame passed as
    # parameter
    def show_frame(self, cont):
        frame = self.frames[cont]
        frame.tkraise()


class StartPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)

        tk.Label(self, text="Welcome to WeChat", bg="#bf8bff", fg="white",
                 height="2", font=("Verdana", 13)).pack(fill='x')
        tk.Label(self, text="", bg='white').pack()

        # Set port label
        tk.Label(self, text="Set Port (1 -> 65535)", bg='white').pack()
        # Set port entry
        self.port_entry = tk.Entry(
            self, width="20", font=("Verdana", 11))
        self.port_entry.pack()
        tk.Label(self, text="", bg='white').pack()

        # create a register button
        tk.Button(self, text="Register", height="2", width="30", bg="#5D0CB5", fg="white", command=lambda: self.enter_app(
            controller=controller, port=self.port_entry.get(), page=RegisterPage)).pack()
        tk.Label(self, text="", bg='white').pack()

        # create a login button
        tk.Button(self, text="Login", height="2", width="30", bg="#A021E2", fg="white", command=lambda: self.enter_app(
            controller=controller, port=self.port_entry.get(), page=LoginPage)).pack()

    def enter_app(self, controller, port, page):
        try:
            port = int(port.strip())
            if not 1 <= port <= MAX_PORT:
                raise ValueError

            # get peer current ip address -> assign to serverhost
            hostname=socket.gethostname()   
            IPAddr=socket.gethostbyname(hostname)  

            # init server
            global network_peer
            network_peer = NetworkPeer(serverhost=IPAddr, serverport=port)
           
            # A child thread for receiving message
            recv_t = threading.Thread(target=network_peer.input_recv)
            recv_t.daemon = True
            recv_t.start()

            # A child thread for receiving file
            recv_file_t = threading.Thread(target=network_peer.recv_file_content)
            recv_file_t.daemon = True
            recv_file_t.start()
            controller.show_frame(page)
        except ValueError:
            self.port_entry.delete(0, tk.END)
            display_noti(
                "Port Error",
                "Enter a valid TCP port from 1 to 55535.\n"
                "Higher ports cannot be used because file transfer uses port + 10000.",
            )
        except OSError as error:
            self.port_entry.delete(0, tk.END)
            display_noti(
                "Port Error",
                "This port is unavailable or already in use.\n\n"
                f"Details: {error}",
            )


class RegisterPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)

        # Sign Up Image
        signup_pic = ImageTk.PhotoImage(asset.signup_image)
        signupImg = tk.Label(self, image=signup_pic, bg='white')
        signupImg.image = signup_pic
        signupImg.place(x=50, y=50)

        form = tk.Frame(self, bg='white', width=320, height=430)
        form.place(x=630, y=65)
        form.grid_propagate(False)
        form.grid_columnconfigure(0, weight=1, minsize=320)

        tk.Label(form, text='Sign Up', fg='#9f63ed', bg='white',
                 font=("Segoe UI", 25, 'bold')).grid(
                     row=0, column=0, pady=(0, 38), sticky='w')
        tk.Label(form, text='Username', bg='white', fg='#438ee8',
                 font=("Segoe UI", 10)).grid(
                     row=1, column=0, pady=(0, 7), sticky='w')
        username_box = tk.Frame(
            form, bg='#f7f4fc', highlightbackground='#d9d1e8',
            highlightcolor='#9f63ed', highlightthickness=1)
        username_box.grid(row=2, column=0, sticky='ew', pady=(0, 25))
        self.username_entry = tk.Entry(
            username_box, fg='#25212d', border=0, bg='#f7f4fc',
            font=("Segoe UI", 11), highlightthickness=0)
        self.username_entry.pack(fill='both', expand=True, padx=12, pady=8)

        tk.Label(form, text='Password', bg='white', fg='#438ee8',
                 font=("Segoe UI", 10)).grid(
                     row=4, column=0, pady=(0, 7), sticky='w')
        password_row = tk.Frame(
            form, bg='#f7f4fc', highlightbackground='#d9d1e8',
            highlightcolor='#9f63ed', highlightthickness=1)
        password_row.grid(row=5, column=0, sticky='ew', pady=(0, 25))
        password_row.configure(width=320, height=42)
        password_row.grid_propagate(False)
        password_row.grid_columnconfigure(0, weight=1, minsize=270)
        password_row.grid_columnconfigure(1, minsize=50)
        self.password_entry = tk.Entry(
            password_row, fg='#25212d', border=0, bg='#f7f4fc',
            font=("Segoe UI", 11), show='*', highlightthickness=0)
        self.password_entry.grid(row=0, column=0, sticky='ew', padx=(12, 0), ipady=8)
        self.password_visible = False
        self.password_toggle = tk.Button(
            password_row, text="Show", width=5, border=0, relief='flat',
            highlightthickness=0, bg='#f7f4fc',
            fg='#438ee8', activebackground='white',
            activeforeground='#2e6fbe', command=self.toggle_password)
        self.password_toggle.grid(row=0, column=1, padx=(8, 0))
        # Submit
        tk.Button(form, text='Sign Up', pady=9, bg='#b478f2',
                  fg='white', border=0, activebackground='#9f63ed',
                  command=lambda: self.register_user(
                      self.username_entry.get(), self.password_entry.get())).grid(
                          row=7, column=0, sticky='ew', pady=(0, 20))
        tk.Label(form, text="Already have an account?", fg='#333333',
                 bg='white', font=("Segoe UI", 10)).grid(
                     row=8, column=0, sticky='w')
        tk.Button(form, text='Sign in', border=0, bg='white',
                  cursor='hand2', fg='#438ee8', activebackground='white',
                  activeforeground='#2e6fbe',
                  command=lambda: controller.show_frame(LoginPage)).grid(
                      row=9, column=0, sticky='w', pady=(4, 0))

    def register_user(self, username, password):
        username = username.strip()
        if not username or len(username) > 32 or not all(
            character.isalnum() or character in "._-" for character in username
        ):
            display_noti(
                "Register Error",
                "Username must be 1-32 characters and contain only letters, numbers, '.', '_' or '-'.",
            )
            return
        if len(password) < 12:
            display_noti("Register Error", "Use a password with at least 12 characters.")
            return

        network_peer.name = username
        network_peer.password = password
        self.username_entry.delete(0, tk.END)
        self.password_entry.delete(0, tk.END)
        network_peer.send_register()

    def toggle_password(self):
        self.password_visible = not self.password_visible
        self.password_entry.config(show='' if self.password_visible else '*')
        self.password_toggle.config(
            text='Hide' if self.password_visible else 'Show')


class LoginPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        # Login Image
        login_pic = ImageTk.PhotoImage(asset.login_image)
        loginImg = tk.Label(self, image=login_pic, bg='white')
        loginImg.image = login_pic
        loginImg.place(x=50, y=50)

        form = tk.Frame(self, bg='white', width=320, height=430)
        form.place(x=630, y=65)
        form.grid_propagate(False)
        form.grid_columnconfigure(0, weight=1, minsize=320)

        tk.Label(form, text='Login', fg='#9f63ed', bg='white',
                 font=("Segoe UI", 25, 'bold')).grid(
                     row=0, column=0, pady=(0, 38), sticky='w')
        tk.Label(form, text='Username', bg='white', fg='#438ee8',
                 font=("Segoe UI", 10)).grid(
                     row=1, column=0, pady=(0, 7), sticky='w')
        username_box = tk.Frame(
            form, bg='#f7f4fc', highlightbackground='#d9d1e8',
            highlightcolor='#9f63ed', highlightthickness=1)
        username_box.grid(row=2, column=0, sticky='ew', pady=(0, 25))
        self.username_entry = tk.Entry(
            username_box, fg='#25212d', border=0, bg='#f7f4fc',
            font=("Segoe UI", 11), highlightthickness=0)
        self.username_entry.pack(fill='both', expand=True, padx=12, pady=8)

        tk.Label(form, text='Password', bg='white', fg='#438ee8',
                 font=("Segoe UI", 10)).grid(
                     row=4, column=0, pady=(0, 7), sticky='w')
        password_row = tk.Frame(
            form, bg='#f7f4fc', highlightbackground='#d9d1e8',
            highlightcolor='#9f63ed', highlightthickness=1)
        password_row.grid(row=5, column=0, sticky='ew', pady=(0, 25))
        password_row.configure(width=320, height=42)
        password_row.grid_propagate(False)
        password_row.grid_columnconfigure(0, weight=1, minsize=270)
        password_row.grid_columnconfigure(1, minsize=50)
        self.password_entry = tk.Entry(
            password_row, fg='#25212d', border=0, bg='#f7f4fc',
            font=("Segoe UI", 11), show='*', highlightthickness=0)
        self.password_entry.grid(row=0, column=0, sticky='ew', padx=(12, 0), ipady=8)
        self.password_visible = False
        self.password_toggle = tk.Button(
            password_row, text="Show", width=5, border=0, relief='flat',
            highlightthickness=0, bg='#f7f4fc',
            fg='#438ee8', activebackground='white',
            activeforeground='#2e6fbe', command=self.toggle_password)
        self.password_toggle.grid(row=0, column=1, padx=(8, 0))
        # Submit
        tk.Button(form, text='Login', pady=9, bg='#b478f2',
                  fg='white', border=0, activebackground='#9f63ed',
                  command=lambda: self.login_user(
                      self.username_entry.get(), self.password_entry.get())).grid(
                          row=7, column=0, sticky='ew', pady=(0, 20))
        tk.Label(form, text="Don't have an account?", fg='#333333',
                 bg='white', font=("Segoe UI", 10)).grid(
                     row=8, column=0, sticky='w')
        tk.Button(form, text='Sign up', border=0, bg='white',
                  cursor='hand2', fg='#438ee8', activebackground='white',
                  activeforeground='#2e6fbe',
                  command=lambda: controller.show_frame(RegisterPage)).grid(
                      row=9, column=0, sticky='w', pady=(4, 0))

    def login_user(self, username, password):
        username = username.strip()
        if not username:
            display_noti("Login Error", "Username is required.")
            self.username_entry.focus_set()
            return
        if not password:
            display_noti("Login Error", "Password is required.")
            self.password_entry.focus_set()
            return

        network_peer.name = username
        network_peer.password = password
        try:
            network_peer.send_login()
        except (ConnectionRefusedError, TimeoutError, OSError) as error:
            display_noti(
                "Login Error",
                "Could not connect to the central server. "
                "Make sure central_server.py is running.\n\n"
                f"Details: {error}",
            )

    def toggle_password(self):
        self.password_visible = not self.password_visible
        self.password_entry.config(show='' if self.password_visible else '*')
        self.password_toggle.config(
            text='Hide' if self.password_visible else 'Show')


class PrivateChatPage(tk.Frame):
    def __init__(self, parent, controller, friend_name):
        tk.Frame.__init__(self, parent)
        self.grid_columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self.friend_name = friend_name
        self.msg = ""

        tk.Label(self, bg="#573d9c", fg="#ffffff", text=friend_name,
                 font="Helvetica 17 bold", pady=15).grid(row=0, column=0, columnspan=2, sticky="news")

        chatroom_icon = ImageTk.PhotoImage(asset.chatroom_icon)
        chatroom_button = tk.Button(self, image=chatroom_icon, border=0,
                                  background="#573d9c", activebackground="#573d9c",
                                  command=lambda: self.open_chatroom())
        chatroom_button.image = chatroom_icon
        chatroom_button.grid(row=0, column=2, columnspan=3, sticky="news")

        self.message_area = tk.Text(
            self, bg="#f2f0f6", fg="#1b142c", font="Helvetica 13", width=1, padx=15, pady=15)
        self.message_area.grid(row=1, column=0, columnspan=3, sticky="news")
        self.message_area.config(cursor="arrow")
        self.message_area.config(state=tk.DISABLED)

        self.entry_msg = tk.Entry(
            self, bg="#ffffff", font="Helvetica 13", highlightthickness=2, highlightcolor="#cbc9ff")
        self.entry_msg.grid(row=2, column=0, sticky="news")

        tk.Button(self, text="Text", width=6, height=1, pady=5,
                  bg="#462d86", fg='#ffffff', font="Helvetica 14 bold",
                  command=lambda: self.sendText(str(self.entry_msg.get()))).grid(row=2, column=1, sticky="news")

        tk.Button(self, text="File", width=6, height=1, pady=5,
                  bg="#ffffff", fg='#462d86', font="Helvetica 14 bold",
                  command=lambda friend=friend_name: self.sendFile(friend)).grid(row=2, column=2, sticky="news")

        # create a scroll bar
        text_scrollbar = tk.Scrollbar(self, orient='vertical')
        text_scrollbar.grid(row=1, column=3, sticky='nse')
        self.message_area.config(yscrollcommand=text_scrollbar.set)
        # Attach the scrollbar with the text widget
        text_scrollbar.config(command=self.message_area.yview)

        self.grid(row=0, column=0, sticky="nsew")

    def sendText(self, msg):
        if msg != "":
            self.msg = msg
            self.entry_msg.delete(0, tk.END)
            st_t = threading.Thread(
                target=network_peer.send_chat_message, args=(self.friend_name, self.msg))
            st_t.daemon = True
            st_t.start()
            # insert messages to text box
            message = network_peer.name + ": " + self.msg
            self.message_area.config(state=tk.NORMAL)
            self.message_area.insert(tk.END, message+"\n\n")
            self.message_area.config(state=tk.DISABLED)
            self.message_area.see(tk.END)

    def sendFile(self, friend_name):
        file_path = tkinter.filedialog.askopenfilename(initialdir=os.getcwd(),
                                                       title="Select a File",
                                                       filetypes=(("All files", "*"),))
        if not file_path:
            return
        file_name = os.path.basename(file_path)
        msg_box = tkinter.messagebox.askquestion('File Explorer', 'Are you sure to send {} to {}?'.format(file_name, friend_name),
                                                 icon="question")
        if msg_box == 'yes':
            sf_t = threading.Thread(
                target=network_peer.transfer_file, args=(self.friend_name, file_path))
            sf_t.daemon = True
            sf_t.start()
            tkinter.messagebox.showinfo(
                "File Transfer", '{} has been sent to {}!'.format(file_name, friend_name))
    
    def open_chatroom(self): 
        chatroom = tk.Toplevel(app)
     
        chatroom.title("Chat room")
        
        chatroom.geometry("470x550")

        labelHead = tk.Label(chatroom,
                               bg="#17202A",
                               fg="#EAECEE",
                               text="WeChat Public Room",
                               font="Helvetica 13 bold",
                               pady=5)
 
        labelHead.place(relwidth=1)
        line = tk.Label(chatroom,
                          width=450,
                          bg="#ABB2B9")
 
        line.place(relwidth=1,
                        rely=0.07,
                        relheight=0.012)
        
     

        app.chatroom_textCons = tk.Text(chatroom,
                             width=20,
                             height=2,
                             bg="#17202A",
                             fg="#EAECEE",
                             font="Helvetica 14",
                             padx=5,
                             pady=5)
 
        app.chatroom_textCons.place(relheight=0.745,
                            relwidth=1,
                            rely=0.08)
 
        labelBottom = tk.Label(chatroom,
                                 bg="#ABB2B9",
                                 height=80)
 
        labelBottom.place(relwidth=1,
                               rely=0.825)
 
        self.entryMsg = tk.Entry(labelBottom,
                              bg="#2C3E50",
                              fg="#EAECEE",
                              font="Helvetica 13")
 
        # place the given widget
        # into the gui window
        self.entryMsg.place(relwidth=0.74,
                            relheight=0.06,
                            rely=0.008,
                            relx=0.011)
 
        self.entryMsg.focus()
 
        # create a Send Button
        self.buttonMsg = tk.Button(labelBottom,
                                text="Send",
                                font="Helvetica 10 bold",
                                width=20,
                                bg="#ABB2B9", command=lambda: self.sendPublicChatButton(self.entryMsg.get()))
 
        self.buttonMsg.place(relx=0.77,
                             rely=0.008,
                             relheight=0.06,
                             relwidth=0.22)
 
        app.chatroom_textCons.config(cursor="arrow")
 
        # create a scroll bar
        scrollbar = tk.Scrollbar(app.chatroom_textCons)
 
        # place the scroll bar
        # into the gui window
        scrollbar.place(relheight=1,
                        relx=0.974)
 
        scrollbar.config(command=app.chatroom_textCons.yview)
 
        app.chatroom_textCons.config(state=tk.DISABLED)
    
        # Display until closed manually
        chatroom.mainloop()
    
    # function to send public messages
    def sendPublicChatButton(self, msg):
        app.chatroom_textCons.config(state=tk.DISABLED)
        self.msg = msg
        self.entryMsg.delete(0, tk.END)
        snd = threading.Thread(target=network_peer.sendPublicMessage, args=(self.msg,))
        snd.daemon = True
        snd.start()
 

class ChatPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)

        self.frame_list = {}

        self.f1 = tk.Frame(self, background="bisque")
        self.f2 = tk.Frame(self, background="yellow")
        self.f3 = tk.Frame(self, background="pink")

        self.f1.grid(row=0, column=0, sticky="nsew")
        self.f2.grid(row=0, column=1, sticky="nsew")
        self.f3.grid(row=0, column=2, sticky="nsew")

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # chat area
        self.f2.grid_columnconfigure(0, weight=1)
        self.f2.grid_rowconfigure(0, weight=1)

        chat_frame = PrivateChatPage(
            parent=self.f2, controller=self, friend_name="MyPrivateMessage")
        self.frame_list["MyPrivateMessage"] = chat_frame
        self.frame_list["MyPrivateMessage"].tkraise()

        # request chat area
        self.f3.grid_columnconfigure(0, weight=1)
        self.f3.grid_rowconfigure(1, weight=1)

        request_label = tk.Label(self.f3, text="Request For Chat", bg="#8372f2",
                                 fg="#e6e6fa", font="Helvetica 13 bold", pady=5, height=2, width=1)
        request_label.grid(row=0, column=0, sticky="news")

        logout_icon = ImageTk.PhotoImage(asset.logout_icon)
        logout_button = tk.Button(self.f3, image=logout_icon, border=0,
                                  background="#8372f2", activebackground="#6a54f7",
                                  command=lambda: self.log_out())
        logout_button.image = logout_icon
        logout_button.grid(row=0, column=1, sticky="news")

        wrapper = tk.Frame(self.f3)
        wrapper.grid(row=1, column=0, columnspan=2, sticky="news")

        wrapper.grid_columnconfigure(0, weight=1)
        wrapper.grid_rowconfigure(0, weight=1)

        mycanvas = tk.Canvas(wrapper, background="#f0f0ff", width=1)
        mycanvas.grid(row=0, column=0, sticky="news")

        yscrollbar = tk.Scrollbar(
            wrapper, orient="vertical", command=mycanvas.yview)
        yscrollbar.grid(row=0, column=1, sticky='ns')

        mycanvas.configure(yscrollcommand=yscrollbar.set)

        mycanvas.bind('<Configure>', lambda e: mycanvas.configure(
            scrollregion=mycanvas.bbox('all')))

        online_frame = tk.Frame(mycanvas)
        mycanvas.create_window((0, 0), window=online_frame)

        reload_icon = ImageTk.PhotoImage(asset.reload_icon)
        reload_button = tk.Button(online_frame, image=reload_icon, border=0,
                                  background="#f0f0ff", activebackground="#eeedff",
                                  command=lambda: self.update_online_user_list())
        reload_button.image = reload_icon
        reload_button.grid(row=0, column=0, sticky="news")

        tk.Label(online_frame, text="Update", background="#f0f0ff", pady=25,
                 font="Helvetica 15 bold").grid(row=0, column=1, sticky="news")

        request_img = ImageTk.PhotoImage(asset.request_image)
        self.user_name_frame = []
        for i in range(1, 100):
            user_img = tk.Label(
                online_frame, image=request_img, background="#f0f0ff")
            user_img.grid(row=i, column=0, sticky="news")
            user_img.image = request_img

            user_name = tk.Button(online_frame, text="Load to see...", width=12, pady=20, background="#f0f0ff",
                                  activebackground="#eeedff", border=0, highlightcolor="#f0f0ff", font="Helvetica 10", fg="#1b142c")
            user_name.grid(row=i, column=1, sticky="news")
            self.user_name_frame.append(user_name)

        # friend area
        self.f1.grid_columnconfigure(0, weight=1)
        self.f1.grid_rowconfigure(1, weight=1)

        send_label = tk.Label(self.f1, text="My Friend List", bg="#cca3ff",
                              fg="#7f00ff", font="Helvetica 13 bold", pady=5, height=2, width=1)
        send_label.grid(row=0, column=0, sticky="nwe")

        wrapper_2 = tk.Frame(self.f1)
        wrapper_2.grid(row=1, column=0, sticky="news")

        wrapper_2.grid_columnconfigure(0, weight=1)
        wrapper_2.grid_rowconfigure(0, weight=1)

        mycanvas_2 = tk.Canvas(wrapper_2, background="#f1e8fc", width=1)
        mycanvas_2.grid(row=0, column=0, sticky="news")

        yscrollbar_2 = tk.Scrollbar(
            wrapper_2, orient="vertical", command=mycanvas_2.yview)
        yscrollbar_2.grid(row=0, column=1, sticky='ns')

        mycanvas_2.configure(yscrollcommand=yscrollbar_2.set)
        mycanvas_2.bind('<Configure>', lambda e: mycanvas_2.configure(
            scrollregion=mycanvas_2.bbox('all')))

        friend_frame = tk.Frame(mycanvas_2)
        mycanvas_2.create_window((0, 0), window=friend_frame)

        reload_button_2 = tk.Button(friend_frame, image=reload_icon, border=0,
                                    background="#f1e8fc", activebackground="#eee3fa",
                                    command=lambda: self.update_friend_list())
        reload_button_2.image = reload_icon
        reload_button_2.grid(row=0, column=0, sticky="news")

        tk.Label(friend_frame, text="Update", background="#f1e8fc", pady=25,
                 font="Helvetica 15 bold").grid(row=0, column=1, sticky="news")

        friend_img = ImageTk.PhotoImage(asset.friend_image)
        self.friend_name_frame = []
        for i in range(1, 100):
            friend_img_container = tk.Label(
                friend_frame, image=friend_img, background="#f1e8fc")
            friend_img_container.image = friend_img
            friend_img_container.grid(row=i, column=0, sticky="news", ipadx=10)

            friend_name = tk.Button(friend_frame, text="Load to see...", width=12, pady=20, background="#f1e8fc",
                                    activebackground="#eee3fa", border=0, highlightcolor="#f0f0ff", font="Helvetica 10", fg="#1b142c")
            friend_name.grid(row=i, column=1, sticky="news")
            self.friend_name_frame.append(friend_name)

    def update_online_user_list(self):
        # request getting online user list
        network_peer.send_listpeer()
        time.sleep(0.1)
        
        for j in range(0, len(self.user_name_frame)):
            self.user_name_frame[j].config(text="Load to see...")
            self.user_name_frame[j].config(command=None)
        
        if len(network_peer.onlinelist) > 0:
            i = 0
            for online_user in network_peer.onlinelist:
                self.user_name_frame[i].config(text=online_user)
                self.user_name_frame[i].config(
                    command=lambda online_user=online_user: self.make_chat_request(online_user))
                i = i+1

    def make_chat_request(self, online_user):
        network_peer.send_request(online_user)

    def update_friend_list(self):
        i = 0
        for key, value in network_peer.friendlist.items():
            self.friend_name_frame[i].config(text=key)
            self.friend_name_frame[i].config(
                command=lambda friend=key: self.raise_private_chat(friend))
            i = i+1

    def raise_private_chat(self, friend):
        chat_frame = PrivateChatPage(
            parent=self.f2, controller=self, friend_name=friend)
        self.frame_list[friend] = chat_frame
        self.frame_list[friend].tkraise()
    
    def log_out(self):
        app.show_frame(LoginPage)
        network_peer.send_logout_request()
## =======================================================##

## ====================CORE IMPLEMENT======================##


class NetworkPeer(Base):
    def __init__(self, serverhost='localhost', serverport=30000, server_info=None):
        super(NetworkPeer, self).__init__(serverhost, serverport)

        # init host and port of central server
        if server_info is None:
            server_info = (socket.gethostbyname(socket.gethostname()), 40000)
        self.server_info = server_info

        # peer name
        self.name = ""
        # peer password
        self.password = ""
        self.session_token = None
        self.authenticated = False

        # all peers it can connect (network peers)
        self.connectable_peer = {}
        self.onlinelist = []
        # peers it has connected (friend)
        self.friendlist = {}

        self.message_format = '{peername}: {message}'
        # file buffer
        self.file_buf = []

        # define handlers for received message of network peer
        handlers = {
            'REGISTER_SUCCESS': self.register_success,
            'REGISTER_ERROR': self.register_error,
            'LOGIN_CHALLENGE': self.login_challenge,
            'LOGIN_SUCCESS': self.login_success,
            'LOGIN_ERROR': self.login_error,
            'LIST_ONLINE_USER': self.get_online_users,
            'CHAT_REQUEST': self.chat_request,
            'CHAT_ACCEPT': self.chat_accept,
            'CHAT_REFUSE': self.chat_refuse,
            'CHAT_MESSAGE': self.recv_message,
            'CHAT_PUBLIC': self.recv_public_message,
        }
        for msgtype, function in handlers.items():
            self.add_handler(msgtype, function)

    ## ==========implement protocol for user registration - network peer==========##
    def send_register(self):
        """ Send a request to server to register peer's information. """
        peer_info = {
            'peername': self.name,
            'password_verifier': hash_password(self.password),
            'host': self.serverhost,
            'port': self.serverport
        }
        self.client_send(self.server_info,
                         msgtype='PEER_REGISTER', msgdata=peer_info)

    def register_success(self, msgdata):
        """ Processing received message from server: Successful registration on the server. """
        display_noti('Register Noti', 'Register Successful.')
        print('Register Successful.')

    def register_error(self, msgdata):
        """ Processing received message from server: Registration failed on the server. """
        display_noti('Register Noti',
                     'Register Error. Username existed or null!')
        print('Register Error. Username existed. Login!')
    ## ===========================================================##

    ## ==========implement protocol for authentication (log in) - network peer==========##
    def send_login(self):
        """ Send a request to server to login. """
        peer_info = {
            'peername': self.name,
            'host': self.serverhost,
            'port': self.serverport
        }
        self.client_send(self.server_info,
                         msgtype='PEER_LOGIN', msgdata=peer_info)

    def login_challenge(self, msgdata):
        """Answer the server's one-time challenge without sending the password."""
        nonce = msgdata.get("nonce")
        if (
            not isinstance(nonce, str)
            or msgdata.get("algorithm") != "pbkdf2_sha256"
            or not isinstance(msgdata.get("iterations"), int)
            or not 100_000 <= msgdata.get("iterations") <= MAX_PASSWORD_ITERATIONS
            or not isinstance(msgdata.get("salt"), str)
        ):
            self.login_error({"reason": "invalid_credentials"})
            return

        try:
            salt = base64.b64decode(msgdata["salt"], validate=True)
            key = derive_password_key(
                self.password,
                salt,
                msgdata["iterations"],
            )
        except (ValueError, TypeError):
            self.login_error({"reason": "invalid_credentials"})
            return

        peer_info = {
            "peername": self.name,
            "host": self.serverhost,
            "port": self.serverport,
            "nonce": nonce,
            "proof": build_login_proof(key, nonce),
        }
        self.client_send(
            self.server_info,
            msgtype="PEER_LOGIN_RESPONSE",
            msgdata=peer_info,
        )

    def login_success(self, msgdata):
        """ Processing received message from server: Successful login on the server. """
        print('Login Successful.')
        display_noti('Login Noti', 'Login Successful.')
        self.session_token = msgdata.get("token")
        self.authenticated = isinstance(self.session_token, str) and bool(self.session_token)
        self.password = ""
        app.frames[LoginPage].username_entry.delete(0, tk.END)
        app.frames[LoginPage].password_entry.delete(0, tk.END)
        app.geometry("1100x600")
        app.resizable(False, False)
        app.show_frame(ChatPage)

    def login_error(self, msgdata):
        """ Processing received message from server: Login failed on the server. """
        detail = 'The username or password is incorrect, or the session has expired.'
        display_noti('Login Error', detail)
        print('Login Error:', detail)
    ## ===========================================================##

    ## ==========implement protocol for getting online user list - network peer==========##
    def send_listpeer(self):
        """ Send a request to server to get all online peers. """
        if not self.authenticated:
            display_noti("Online Users", "Please log in first.")
            return
        peer_info = {
            'peername': self.name,
            'host': self.serverhost,
            'port': self.serverport,
            'token': self.session_token,
        }
        self.client_send(self.server_info,
                         msgtype='PEER_LIST', msgdata=peer_info)

    def get_online_users(self, msgdata):
        """ Processing received message from server:
            Output username of all peers that have been registered on the server and are online."""
        self.connectable_peer.clear()
        for key, value in msgdata['online_user_list'].items():
            self.connectable_peer[key] = tuple(value)
        if self.name in self.connectable_peer:
            self.connectable_peer.pop(self.name)
        self.onlinelist = [key for key, value in self.connectable_peer.items()]
    ## ===========================================================##

    ## ==========implement protocol for chat request (can upgrade to friend request)==========##
    def send_request(self, peername):
        """ Send a chat request to an online user. """
        if peername not in self.friendlist:
            try:
                server_info = self.connectable_peer[peername]
            except KeyError:
                display_noti("Chat Request Error",
                             'This peer ({}) is not available.'.format(peername))
            else:
                data = {
                    'peername': self.name,
                    'host': self.serverhost,
                    'port': self.serverport
                }
                self.client_send(
                    server_info, msgtype='CHAT_REQUEST', msgdata=data)
        else:
            display_noti("Chat Request Error",
                         'You have already connected to {}.'.format(peername))

    def chat_request(self, msgdata, address):
        """ Processing received chat request message from peer. """
        peername = msgdata['peername']
        host, port = msgdata['host'], msgdata['port']
        if address is None or address[0] != host or self.connectable_peer.get(peername) != (host, port):
            return
        msg_box = tk.messagebox.askquestion('Chat Request', 'Do you want to accept {} - {}:{}?'.format(peername, host, port),
                                            icon="question")
        if msg_box == 'yes':
            # if request is agreed, connect to peer (add to friendlist)
            data = {
                'peername': self.name,
                'host': self.serverhost,
                'port': self.serverport
            }
            self.client_send((host, port), msgtype='CHAT_ACCEPT', msgdata=data)
            display_noti("Chat Request Accepted",
                         "Update to get in touch with new friend!")
            self.friendlist[peername] = (host, port)
        else:
            self.client_send((host, port), msgtype='CHAT_REFUSE', msgdata={
                'peername': self.name,
                'host': self.serverhost,
                'port': self.serverport,
            })

    def chat_accept(self, msgdata, address):
        """ Processing received accept chat request message from peer.
            Add the peer to collection of friends. """
        peername = msgdata['peername']
        host = msgdata['host']
        port = msgdata['port']
        if address is None or address[0] != host or self.connectable_peer.get(peername) != (host, port):
            return
        display_noti("Chat Request Result",
                     'CHAT ACCEPTED: {} --- {}:{}. Update to get in touch with new friend!'.format(peername, host, port))
        self.friendlist[peername] = (host, port)

    def chat_refuse(self, msgdata, address):
        """ Processing received refuse chat request message from peer. """
        host = msgdata.get('host')
        peername = msgdata.get('peername')
        if (
            address is None
            or not isinstance(host, str)
            or address[0] != host
            or self.connectable_peer.get(peername) != (host, msgdata.get('port'))
        ):
            return
        display_noti("Chat Request Result", 'CHAT REFUSED!')
    ## ===========================================================##

    ## ==========implement protocol for public messaging==========##
    def sendPublicMessage(self, message):
        """ Send a chat message to public community. """
        if not self.authenticated:
            display_noti("Public Messaging Result", "Please log in first.")
            return
        data = {
            'peername': self.name,
            'message': message,
            'token': self.session_token,
        }
        self.client_send(self.server_info, msgtype='PUBLIC_CHAT', msgdata=data)
    
    def recv_public_message(self, msgdata, address):
        """ Processing received public chat message from central server."""
        if address is None or address[0] != self.server_info[0]:
            return
        # insert messages to text box
        message = msgdata['name'] + ": " + msgdata['message']
        app.chatroom_textCons.config(state=tk.NORMAL)
        app.chatroom_textCons.insert(tk.END, message+"\n\n")
        app.chatroom_textCons.config(state=tk.DISABLED)
        app.chatroom_textCons.see(tk.END)
    ## ===========================================================##

    ## ==========implement protocol for text messaging==========##
    def send_chat_message(self, friend, message):
        """ Send a chat message to friend. """
        try:
            peer_info = self.friendlist[friend]
        except KeyError:
            display_noti("Text Messaging Result", 'Friend does not exist!')
        else:
            data = {
                'friend_name': self.name,
                'message': message
            }
            self.client_send(peer_info, msgtype='CHAT_MESSAGE', msgdata=data)

    def recv_message(self, msgdata, address):
        """ Processing received chat message from peer."""
        friend_name = msgdata['friend_name']
        friend = self.friendlist.get(friend_name)
        if friend is not None and address is not None and address[0] == friend[0]:
            # insert messages to text box
            message = friend_name + ": " + msgdata['message']
            app.frames[ChatPage].frame_list[friend_name].message_area.config(
                state=tk.NORMAL)
            app.frames[ChatPage].frame_list[friend_name].message_area.insert(
                tk.END, message+"\n\n")
            app.frames[ChatPage].frame_list[friend_name].message_area.config(
                state=tk.DISABLED)
            app.frames[ChatPage].frame_list[friend_name].message_area.see(
                tk.END)
    ## ===========================================================##

    ## ==========implement protocol for file tranfering==========##
    def transfer_file(self, peer, file_path):
        """ Transfer a file to friend. """
        try:
            peer_info = self.friendlist[peer]
        except KeyError:
            display_noti("File Transfer Result", 'Friend does not exist!')
        else:
            file_name = os.path.basename(file_path)

            def fileThread(filename):
                try:
                    file_size = os.path.getsize(file_path)
                    if file_size > MAX_FILE_SIZE:
                        display_noti(
                            "File Transfer Result",
                            f"Files must be smaller than {MAX_FILE_SIZE // (1024 * 1024)} MB.",
                        )
                        return

                    file_sent = socket.create_connection(
                        (peer_info[0], peer_info[1] + OFFSET),
                        timeout=10,
                    )
                    try:
                        Base.send_json(
                            file_sent,
                            {
                                "filename": filename,
                                "friendname": peer,
                                "filesize": file_size,
                            },
                        )
                        response = Base.recv_json(file_sent)
                        if response.get("accepted") is not True:
                            display_noti(
                                "File Transfer Result",
                                "The recipient declined the file.",
                            )
                            return

                        with open(file_path, "rb") as file_handle:
                            remaining = file_size
                            while remaining:
                                bytes_read = file_handle.read(min(BUFFER_SIZE, remaining))
                                if not bytes_read:
                                    raise OSError("File changed while it was being sent")
                                file_sent.sendall(bytes_read)
                                remaining -= len(bytes_read)
                        display_noti("File Transfer Result", "File has been sent!")
                    finally:
                        file_sent.close()
                except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
                    display_noti("File Transfer Result", f"File transfer failed: {error}")

            t_sf = threading.Thread(
                target=fileThread,
                args=(file_name,),
                daemon=True,
            )
            t_sf.start()

    def recv_file_content(self):
        """ Processing received file content from peer."""
        self.file_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.file_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # bind the socket to our local address
        self.file_socket.bind((self.serverhost, int(self.serverport) + OFFSET))
        self.file_socket.listen(5)

        while True:
            conn, addr = self.file_socket.accept()
            receive_thread = threading.Thread(
                target=self._receive_file,
                args=(conn, addr),
                daemon=True,
            )
            receive_thread.start()

    def _receive_file(self, conn, addr):
        try:
            conn.settimeout(30)
            recv_file_info = Base.recv_json(conn)
            filename = recv_file_info.get("filename")
            friend_name = recv_file_info.get("friendname")
            file_size = recv_file_info.get("filesize")

            safe_name = os.path.basename(filename) if isinstance(filename, str) else ""
            sender = self.friendlist.get(friend_name)
            valid_sender = (
                isinstance(friend_name, str)
                and sender is not None
                and sender[0] == addr[0]
                and safe_name == filename
                and safe_name not in ("", ".", "..")
                and "\x00" not in safe_name
                and isinstance(file_size, int)
                and 0 <= file_size <= MAX_FILE_SIZE
            )
            if not valid_sender:
                Base.send_json(conn, {"accepted": False})
                print(f"Rejected invalid file transfer from {addr}")
                return

            accepted = tkinter.messagebox.askyesno(
                "File Transfer",
                f"Accept '{safe_name}' from {friend_name}?",
            )
            if not accepted:
                Base.send_json(conn, {"accepted": False})
                return

            DOWNLOAD_DIR.mkdir(exist_ok=True)
            target_path = DOWNLOAD_DIR / f"{secrets.token_hex(8)}_{safe_name}"
            Base.send_json(conn, {"accepted": True})
            with target_path.open("wb") as file_handle:
                remaining = file_size
                while remaining:
                    chunk = conn.recv(min(BUFFER_SIZE, remaining))
                    if not chunk:
                        raise ConnectionError(
                            "File transfer ended before the declared size"
                        )
                    file_handle.write(chunk)
                    remaining -= len(chunk)

            display_noti(
                "File Transfer Result",
                f"You received '{safe_name}' from {friend_name}.\n"
                f"Saved to {target_path}",
            )
        except (
            ConnectionError,
            OSError,
            ValueError,
            TypeError,
            KeyError,
            json.JSONDecodeError,
        ) as error:
            print(f"File transfer from {addr} failed: {error}")
        finally:
            conn.close()
    
    ## ===========================================================##
    
    ## ==========implement protocol for log out & exit ===================##

    def send_logout_request(self):
        """ Central Server deletes user out of online user list """
        if not self.authenticated:
            return
        peer_info = {
            'peername': self.name,
            'port': self.serverport,
            'token': self.session_token,
        }
        try:
            self.client_send(
                self.server_info,
                msgtype='PEER_LOGOUT',
                msgdata=peer_info,
            )
        finally:
            self.authenticated = False
            self.session_token = None

    ## ===========================================================##

## ===========================================================##
## ===========================================================##
network_peer = None
app = tkinterApp()
app.title('Chat App')
app.geometry("1024x600")
app.resizable(False, False)

def handle_on_closing_event():
    if tkinter.messagebox.askokcancel("Quit", "Do you want to quit?"):
        try:
            if network_peer is not None:
                network_peer.send_logout_request()
        except OSError as error:
            print(f"Could not notify the server during logout: {error}")
        app.destroy()

app.protocol("WM_DELETE_WINDOW", handle_on_closing_event)
app.mainloop()
