from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import render, redirect
from django.urls import reverse


class LoginCheckMiddleWare(MiddlewareMixin):
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        modulename = view_func.__module__
        # print(modulename)
        user = request.user

        #Check whether the user is logged in or not
        if user.is_authenticated:
            if user.user_type == "1":
                if modulename == "student_management_app.HodViews":
                    pass
                elif modulename == "student_management_app.views" or modulename == "django.views.static":
                    pass
                elif modulename == "chatbot.views":
                    # Allow chatbot views for HOD
                    pass
                else:
                    return redirect("admin_home")
            
            elif user.user_type == "2":
                if modulename == "student_management_app.StaffViews":
                    pass
                elif modulename == "student_management_app.views" or modulename == "django.views.static":
                    pass
                elif modulename == "chatbot.views":
                    # Allow chatbot views for Staff
                    pass
                else:
                    return redirect("staff_home")
            
            elif user.user_type == "3":
                if modulename == "student_management_app.StudentViews":
                    pass
                elif modulename == "student_management_app.views" or modulename == "django.views.static":
                    pass
                elif modulename == "chatbot.views":
                    # Allow chatbot views for Student
                    pass
                else:
                    return redirect("student_home")

            else:
                return redirect("login")

        else:
            # Allow unauthenticated users to access password reset and login pages
            allowed_urls = [
                reverse("login"),
                reverse("doLogin"),
                reverse("password_reset_request"),
                reverse("password_reset_verify"),
                reverse("password_reset_resend_otp"),
                reverse("password_reset_new"),
            ]
            
            if request.path in allowed_urls:
                pass
            else:
                return redirect("login")
