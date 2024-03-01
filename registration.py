import asyncio
import sys
from tkinter import Label, Entry, Button, Tk, CENTER, messagebox

from environs import Env

from send_message_to_chat import register


class Block:
    def __init__(self, master, func, host, port, file_path):
        self.ent = Entry(master, width=30)
        self.but = Button(master, text='Зарегистрироваться')
        self.lab = Label(master, width=50, fg='black', text='Введи ваш Nickname', pady=20)

        self.host = host
        self.port = port
        self.file_path = file_path

        self.but['command'] = getattr(self, func)
        self.ent.pack()
        self.but.pack()
        self.lab.pack()

    def send_registration(self):
        try:
            nickname = self.ent.get()
            if nickname.strip() == '':
                messagebox.showwarning('Предупреждение', 'Поле не должно быть пустым!')
                return

            registration_result = asyncio.run(register(self.host, self.port, nickname, self.file_path))
            if isinstance(registration_result, Exception):
                raise registration_result
            elif registration_result:
                messagebox.showinfo('Информация', f'Данные для авторизации уже есть в '
                                                  f'{self.file_path}')
            else:
                messagebox.showinfo('Информация', f'Вы зарегистрировались, данные записаны '
                                                  f'в файл - {self.file_path}')
        except Exception as error:
            messagebox.showerror('Ошибка', f'Произошла ошибка: {repr(error)}')
        finally:
            sys.exit()


if __name__ == '__main__':
    env = Env()
    env.read_env()

    chat_host = env.str('HOST', 'minechat.dvmn.org')
    send_message_chat_port = env.str('SEND_MESSAGE_PORT', '5050')
    user_file_path = env.str('USER_FILE_PATH', 'user.json')

    root = Tk()
    root.title('Регистрация')

    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    window_width = 300
    window_height = 200

    cord_x = (screen_width - window_width) // 2
    cord_y = (screen_height - window_height) // 2

    root.geometry(f'{window_width}x{window_height}+{cord_x}+{cord_y}')

    first_block = Block(root, 'send_registration', chat_host, send_message_chat_port, user_file_path)

    first_block.ent.place(relx=0.5, rely=0.4, anchor=CENTER)
    first_block.but.place(relx=0.5, rely=0.6, anchor=CENTER)

    root.mainloop()
