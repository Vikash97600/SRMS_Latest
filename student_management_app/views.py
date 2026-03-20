# from channels.auth import login, logout
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from django.conf import settings
import random

from student_management_app.EmailBackEnd import EmailBackEnd
from student_management_app.models import PasswordReset, CustomUser


def home(request):
    return render(request, 'index.html')


def loginPage(request):
    return render(request, 'login.html')



def doLogin(request):
    if request.method != "POST":
        return HttpResponse("<h2>Method Not Allowed</h2>")
    else:
        user = EmailBackEnd.authenticate(request, username=request.POST.get('email'), password=request.POST.get('password'))
        if user != None:
            login(request, user)
            user_type = user.user_type
            #return HttpResponse("Email: "+request.POST.get('email')+ " Password: "+request.POST.get('password'))
            if user_type == '1':
                return redirect('admin_home')
                
            elif user_type == '2':
                # return HttpResponse("Staff Login")
                return redirect('staff_home')
                
            elif user_type == '3':
                # return HttpResponse("Student Login")
                return redirect('student_home')
            else:
                messages.error(request, "Invalid Login!")
                return redirect('login')
        else:
            messages.error(request, "Invalid Login Credentials!")
            #return HttpResponseRedirect("/")
            return redirect('login')



def get_user_details(request):
    if request.user != None:
        return HttpResponse("User: "+request.user.email+" User Type: "+request.user.user_type)
    else:
        return HttpResponse("Please Login First")



def logout_user(request):
    logout(request)
    return HttpResponseRedirect('/')


def password_reset_request(request):
    """View to handle password reset request - enter email"""
    if request.user.is_authenticated:
        return redirect('login')
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        
        if not email:
            messages.error(request, 'Please enter your email address.')
            return render(request, 'password_reset_request.html')
        
        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, 'Please enter a valid email address.')
            return render(request, 'password_reset_request.html')
        
        # Check if user exists with this email
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            # Don't reveal that the user doesn't exist for security
            messages.success(request, 'If an account exists with this email, you will receive password reset instructions shortly.')
            return render(request, 'password_reset_request.html')
        
        # Generate reset token and OTP
        reset_token = PasswordReset.generate_token()
        otp_code = PasswordReset.generate_otp()
        
        # Get IP address and user agent
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
        
        # Create password reset record
        password_reset = PasswordReset.objects.create(
            user=user,
            reset_token=reset_token,
            otp_code=otp_code,
            email=email,
            expires_at=timezone.now() + timedelta(hours=24),
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Send email with reset link and OTP
        try:
            send_password_reset_email(email, reset_token, otp_code, user.get_full_name() or user.username)
            messages.success(request, 'If an account exists with this email, you will receive password reset instructions shortly.')
            # Store the reset token in session for verification step
            request.session['password_reset_email'] = email
            request.session['password_reset_token'] = reset_token
            return redirect('password_reset_verify')
        except Exception as e:
            messages.error(request, 'Unable to send password reset email. Please try again later.')
            return render(request, 'password_reset_request.html')
    
    return render(request, 'password_reset_request.html')


def password_reset_verify(request):
    """View to verify OTP for password reset"""
    if request.user.is_authenticated:
        return redirect('login')
    
    email = request.session.get('password_reset_email')
    reset_token = request.session.get('password_reset_token')
    
    if not email or not reset_token:
        messages.error(request, 'Invalid password reset session. Please start the process again.')
        return redirect('password_reset_request')
    
    # Check if token exists and is valid
    try:
        password_reset = PasswordReset.objects.get(email=email, reset_token=reset_token)
        if not password_reset.is_valid():
            messages.error(request, 'This password reset link has expired. Please request a new one.')
            return redirect('password_reset_request')
    except PasswordReset.DoesNotExist:
        messages.error(request, 'Invalid password reset token. Please request a new one.')
        return redirect('password_reset_request')
    
    if request.method == 'POST':
        otp_code = request.POST.get('otp_code', '').strip()
        
        if not otp_code:
            messages.error(request, 'Please enter the OTP code.')
            return render(request, 'password_reset_verify.html', {'email': email})
        
        if len(otp_code) != 6 or not otp_code.isdigit():
            messages.error(request, 'Please enter a valid 6-digit OTP code.')
            return render(request, 'password_reset_verify.html', {'email': email})
        
        # Verify OTP
        if password_reset.otp_code == otp_code:
            if not password_reset.is_otp_valid():
                messages.error(request, 'This OTP has expired. Please request a new one.')
                return redirect('password_reset_request')
            
            # OTP verified successfully - store in session and redirect to new password page
            request.session['password_reset_verified'] = True
            return redirect('password_reset_new')
        else:
            # Increment failed attempts
            password_reset.otp_attempts = getattr(password_reset, 'otp_attempts', 0) + 1
            password_reset.save()
            
            if getattr(password_reset, 'otp_attempts', 0) >= 5:
                messages.error(request, 'Too many failed attempts. Please request a new password reset.')
                password_reset.delete()
                return redirect('password_reset_request')
            
            messages.error(request, 'Invalid OTP code. Please try again.')
            return render(request, 'password_reset_verify.html', {'email': email})
    
    # Check if we can resend OTP
    can_resend = True
    time_since_created = timezone.now() - password_reset.created_at
    if time_since_created < timedelta(minutes=1):
        can_resend = False
    
    return render(request, 'password_reset_verify.html', {
        'email': email,
        'can_resend': can_resend
    })


def password_reset_resend_otp(request):
    """Resend OTP for password reset"""
    if request.user.is_authenticated:
        return redirect('login')
    
    email = request.session.get('password_reset_email')
    reset_token = request.session.get('password_reset_token')
    
    if not email or not reset_token:
        messages.error(request, 'Invalid password reset session. Please start the process again.')
        return redirect('password_reset_request')
    
    try:
        password_reset = PasswordReset.objects.get(email=email, reset_token=reset_token)
        if not password_reset.is_valid():
            messages.error(request, 'This password reset link has expired. Please request a new one.')
            return redirect('password_reset_request')
        
        # Check if we can resend (1 minute cooldown)
        time_since_created = timezone.now() - password_reset.created_at
        if time_since_created < timedelta(minutes=1):
            messages.error(request, 'Please wait at least 1 minute before requesting a new OTP.')
            return redirect('password_reset_verify')
        
        # Generate new OTP
        new_otp = PasswordReset.generate_otp()
        password_reset.otp_code = new_otp
        password_reset.save()
        
        # Resend email
        user = password_reset.user
        try:
            send_password_reset_email(email, reset_token, new_otp, user.get_full_name() or user.username)
            messages.success(request, 'A new OTP has been sent to your email address.')
        except Exception:
            messages.error(request, 'Unable to send OTP. Please try again later.')
    
    except PasswordReset.DoesNotExist:
        messages.error(request, 'Invalid password reset session. Please start the process again.')
        return redirect('password_reset_request')
    
    return redirect('password_reset_verify')


def password_reset_new(request):
    """View to set new password after verification"""
    if request.user.is_authenticated:
        return redirect('login')
    
    email = request.session.get('password_reset_email')
    reset_token = request.session.get('password_reset_token')
    verified = request.session.get('password_reset_verified')
    
    if not email or not reset_token or not verified:
        messages.error(request, 'Invalid password reset session. Please start the process again.')
        return redirect('password_reset_request')
    
    # Verify token is still valid
    try:
        password_reset = PasswordReset.objects.get(email=email, reset_token=reset_token)
        if not password_reset.is_valid():
            messages.error(request, 'This password reset link has expired. Please request a new one.')
            return redirect('password_reset_request')
    except PasswordReset.DoesNotExist:
        messages.error(request, 'Invalid password reset token. Please request a new one.')
        return redirect('password_reset_request')
    
    if request.method == 'POST':
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        
        # Validate password
        errors = validate_password_strength(password, confirm_password)
        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'password_reset_new.html', {'email': email})
        
        # Update user's password
        try:
            user = CustomUser.objects.get(email=email)
            user.set_password(password)
            user.save()
            
            # Mark reset token as used
            password_reset.is_used = True
            password_reset.save()
            
            # Clear session
            request.session.pop('password_reset_email', None)
            request.session.pop('password_reset_token', None)
            request.session.pop('password_reset_verified', None)
            
            # Delete old unused reset tokens for this user
            PasswordReset.objects.filter(user=user, is_used=False).delete()
            
            messages.success(request, 'Your password has been reset successfully. Please login with your new password.')
            return redirect('login')
        
        except CustomUser.DoesNotExist:
            messages.error(request, 'User not found. Please request a new password reset.')
            return redirect('password_reset_request')
    
    return render(request, 'password_reset_new.html', {'email': email})


def validate_password_strength(password, confirm_password):
    """Validate password strength and matching"""
    errors = []
    
    if password != confirm_password:
        errors.append('Passwords do not match.')
    
    if len(password) < 8:
        errors.append('Password must be at least 8 characters long.')
    
    if not any(c.isupper() for c in password):
        errors.append('Password must contain at least one uppercase letter.')
    
    if not any(c.islower() for c in password):
        errors.append('Password must contain at least one lowercase letter.')
    
    if not any(c.isdigit() for c in password):
        errors.append('Password must contain at least one number.')
    
    # Check for special characters
    special_chars = '!@#$%^&*()_+-=[]{}|;:,.<>?'
    if not any(c in special_chars for c in password):
        errors.append(f'Password must contain at least one special character ({special_chars}).')
    
    return errors


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def send_password_reset_email(email, token, otp, username):
    """Send password reset email with reset link and OTP"""
    subject = 'TIMSCDR - Password Reset Request'
    
    # HTML message
    message_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%); padding: 30px; border-radius: 10px 10px 0 0;">
                <h1 style="color: #fff; margin: 0; text-align: center;">TIMSCDR</h1>
                <p style="color: #fff; text-align: center; margin: 10px 0 0 0;">Student Record Management System</p>
            </div>
            <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
                <h2 style="color: #1e3a5f;">Hello {username},</h2>
                <p>We received a request to reset your password for your TIMSCDR account.</p>
                
                <div style="background: #fff; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #2d5a87;">
                    <h3 style="margin: 0 0 15px 0; color: #1e3a5f;">Your Verification Code (OTP):</h3>
                    <p style="font-size: 24px; font-weight: bold; color: #2d5a87; letter-spacing: 5px; text-align: center; margin: 0;">{otp}</p>
                    <p style="font-size: 12px; color: #666; text-align: center; margin: 10px 0 0 0;">This code is valid for 15 minutes</p>
                </div>
                
                <p style="color: #666; font-size: 14px;">
                    <strong>Security Notice:</strong>
                    <ul style="color: #666; font-size: 14px;">
                        <li>This OTP can be used only once</li>
                        <li>Do not share this code with anyone</li>
                        <li>If you didn't request this, please ignore this email</li>
                    </ul>
                </p>
                
                <p style="margin-top: 30px; color: #666; font-size: 14px;">
                    If you need any assistance, please contact the system administrator.
                </p>
                
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center;">
                    <p style="color: #999; font-size: 12px; margin: 0;">&copy; {timezone.now().year} TIMSCDR. All rights reserved.</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Plain text message
    message_text = f"""
    TIMSCDR - Password Reset Request
    
    Hello {username},
    
    We received a request to reset your password for your TIMSCDR account.
    
    Your Verification Code (OTP): {otp}
    
    This code is valid for 15 minutes.
    
    Security Notice:
    - This OTP can be used only once
    - Do not share this code with anyone
    - If you didn't request this, please ignore this email
    
    If you need any assistance, please contact the system administrator.
    
    © {timezone.now().year} TIMSCDR. All rights reserved.
    """
    
    from django.core.mail import EmailMultiAlternatives
    from django.template.loader import render_to_string
    from django.utils.html import strip_tags
    
    # Try to send email
    try:
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@timscdr.edu')
        
        msg = EmailMultiAlternatives(subject, message_text, from_email, [email])
        msg.attach_alternative(message_html, "text/html")
        msg.send(fail_silently=False)
    except Exception as e:
        # Log the error but don't expose it to user
        print(f"Email send error: {e}")
        # For development, we'll print the OTP to console
        print(f"DEV MODE - OTP for {email}: {otp}")


